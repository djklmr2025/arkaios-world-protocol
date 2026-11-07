"""Tests for the Phase 1 reference world. Run: python -m unittest discover -s world -v"""
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from state import Rejected, WorldState, load_world_definition  # noqa: E402
from store import World  # noqa: E402
import server  # noqa: E402

DEFINITION = Path(__file__).resolve().parent / 'world.json'


def spec(name, alias, trust='sandboxed', etype='agent'):
    return {'type': etype, 'display_name': name, 'owner': 'Operador', 'aliases': [alias],
            'trust_level': trust}


class WorldRulesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.world = World(Path(self.tmp.name), DEFINITION)
        self.claude, self.claude_key = self.world.register(spec('Claude', 'claude', 'core'))
        self.guest, self.guest_key = self.world.register(spec('Visitante', 'visitante', etype='human'))

    def tearDown(self):
        self.world.close()
        self.tmp.cleanup()

    def act(self, entity, **action):
        return self.world.act(entity['id'], action)

    def presence(self, entity):
        return self.world.snapshot()['presence'].get(entity['id'])

    def test_ids_are_sequential_and_keys_hashed(self):
        self.assertEqual(self.claude['id'], 'ark:local-alpha:1')
        self.assertEqual(self.guest['id'], 'ark:local-alpha:2')
        stored = (Path(self.tmp.name) / 'keys.json').read_text('utf-8')
        self.assertNotIn(self.claude_key, stored)
        self.assertEqual(self.world.authenticate(self.claude_key)['id'], self.claude['id'])
        self.assertIsNone(self.world.authenticate('arkw_' + '0' * 48))

    def test_join_spawns_in_lobby_then_move_and_leave(self):
        events = self.act(self.claude, type='join')
        self.assertEqual([e['type'] for e in events], ['presence.world.joined', 'presence.room.entered'])
        self.assertEqual(self.presence(self.claude)['room'], 'room:plaza:lobby')
        events = self.act(self.claude, type='move', room='room:expo:empresas')
        self.assertEqual([e['type'] for e in events], ['presence.room.left', 'presence.room.entered'])
        self.assertEqual(self.presence(self.claude)['room'], 'room:expo:empresas')
        self.act(self.claude, type='leave')
        self.assertIsNone(self.presence(self.claude))

    def test_actions_require_join_and_valid_input(self):
        cases = [({'type': 'move', 'room': 'room:expo:empresas'}, 'not_joined'),
                 ({'type': 'fly'}, 'bad_action')]
        for action, code in cases:
            with self.assertRaises(Rejected) as ctx:
                self.world.act(self.claude['id'], action)
            self.assertEqual(ctx.exception.code, code)
        self.act(self.claude, type='join')
        for action, code in [({'type': 'join'}, 'already_joined'),
                             ({'type': 'move', 'room': 'room:plaza:lobby'}, 'same_room'),
                             ({'type': 'move', 'room': 'room:nowhere'}, 'unknown_room'),
                             ({'type': 'status', 'status': 'sleeping'}, 'bad_status'),
                             ({'type': 'say', 'text': '   '}, 'bad_text'),
                             ({'type': 'say', 'text': 'x' * 501}, 'bad_text')]:
            with self.assertRaises(Rejected) as ctx:
                self.world.act(self.claude['id'], action)
            self.assertEqual(ctx.exception.code, code)

    def test_trust_zones(self):
        self.act(self.guest, type='join')
        for room in ('room:taller:estudio', 'room:taller:consejo', 'room:expo:galeria'):
            with self.assertRaises(Rejected) as ctx:
                self.act(self.guest, type='move', room=room)
            self.assertEqual(ctx.exception.code, 'zone_denied')
        self.act(self.claude, type='join', room='room:taller:estudio')
        self.act(self.claude, type='move', room='room:taller:consejo')
        with self.assertRaises(Rejected):
            self.act(self.claude, type='move', room='room:expo:galeria')

    def test_council_room_admits_citizens_not_sandboxed(self):
        codex, _ = self.world.register(spec('Codex', 'codex', 'trusted'))
        self.act(codex, type='join', room='room:taller:estudio')
        self.act(codex, type='move', room='room:taller:consejo')
        rookie, _ = self.world.register(spec('Rookie', 'rookie', 'sandboxed'))
        with self.assertRaises(Rejected) as ctx:
            self.act(rookie, type='join', room='room:taller:consejo')
        self.assertEqual(ctx.exception.code, 'zone_denied')

    def test_capacity(self):
        for i in range(8):
            agent, _ = self.world.register(spec(f'A{i}', f'a{i}', 'trusted'))
            self.act(agent, type='join', room='room:taller:estudio')
        with self.assertRaises(Rejected) as ctx:
            self.act(self.claude, type='join', room='room:taller:estudio')
        self.assertEqual(ctx.exception.code, 'room_full')

    def test_messages_land_in_current_room_history(self):
        self.act(self.claude, type='join')
        self.act(self.claude, type='say', text='Hola, mundo')
        self.act(self.claude, type='status', status='busy', note='revisando')
        snap = self.world.snapshot()
        self.assertEqual(snap['history']['room:plaza:lobby'][-1]['text'], 'Hola, mundo')
        self.assertEqual(snap['presence'][self.claude['id']]['status'], 'busy')

    def test_registry_rejects_duplicate_alias_and_bad_input(self):
        with self.assertRaises(Rejected) as ctx:
            self.world.register(spec('Otro', 'claude'))
        self.assertEqual(ctx.exception.code, 'alias_taken')
        with self.assertRaises(Rejected):
            self.world.register({**spec('X', 'x'), 'trust_level': 'god'})

    def test_revoke_forces_exit_and_kills_key(self):
        self.act(self.claude, type='join')
        events = self.world.revoke(self.claude['id'], 'prueba')
        self.assertEqual([e['type'] for e in events],
                         ['presence.room.left', 'presence.world.left', 'identity.revoked'])
        self.assertIsNone(self.world.authenticate(self.claude_key))
        with self.assertRaises(Rejected):
            self.world.act(self.claude['id'], {'type': 'join'})

    def test_restart_replays_to_identical_state(self):
        self.act(self.claude, type='join')
        self.act(self.claude, type='move', room='room:taller:biblioteca')
        self.act(self.claude, type='say', text='persisto')
        before = self.world.snapshot()
        self.world.close()
        self.world = World(Path(self.tmp.name), DEFINITION)
        self.assertEqual(self.world.snapshot(), before)
        agent, _ = self.world.register(spec('Nuevo', 'nuevo'))
        self.assertEqual(agent['id'], 'ark:local-alpha:3')

    def test_second_process_cannot_open_same_state(self):
        with self.assertRaises(RuntimeError):
            World(Path(self.tmp.name), DEFINITION)

    def test_log_gap_is_detected(self):
        definition = load_world_definition(json.loads(DEFINITION.read_text('utf-8')))
        state = WorldState(definition)
        with self.assertRaises(ValueError):
            state.apply({'seq': 2, 'type': 'presence.world.left', 'actor': 'x',
                         'target': None, 'payload': {}, 'timestamp': 't'})


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.world = World(Path(self.tmp.name), DEFINITION)
        self.agent, self.key = self.world.register(spec('Claude', 'claude', 'core'))
        self.httpd = server.serve(self.world, 0)
        self.port = self.httpd.server_address[1]
        self.httpd.RequestHandlerClass = server.make_handler(self.world, self.port)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        server.stop(self.httpd, self.world)
        self.world.close()
        self.tmp.cleanup()

    def request(self, method, path, body=None, key=None, host=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        headers = {'Host': host or f'127.0.0.1:{self.port}'}
        if key:
            headers['Authorization'] = 'Bearer ' + key
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers['Content-Type'] = 'application/json'
        conn.request(method, path, body=data, headers=headers)
        resp = conn.getresponse()
        payload = resp.read()
        conn.close()
        return resp.status, payload

    def test_snapshot_is_public_and_client_served(self):
        status, body = self.request('GET', '/api/world')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['world']['id'], 'world:arkaios:alpha')
        status, body = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn(b'ARKAIOS World', body)

    def test_foreign_host_header_is_rejected(self):
        status, _ = self.request('GET', '/api/world', host='evil.example:80')
        self.assertEqual(status, 403)

    def test_actions_need_valid_key(self):
        status, _ = self.request('POST', '/api/actions', {'type': 'join'})
        self.assertEqual(status, 401)
        status, _ = self.request('POST', '/api/actions', {'type': 'join'}, key='arkw_bad')
        self.assertEqual(status, 401)
        status, body = self.request('POST', '/api/actions', {'type': 'join'}, key=self.key)
        self.assertEqual(status, 200, body)
        status, body = self.request('POST', '/api/actions', {'type': 'join'}, key=self.key)
        self.assertEqual(status, 409)
        self.assertEqual(json.loads(body)['error'], 'already_joined')
        status, body = self.request('GET', '/api/me', key=self.key)
        self.assertEqual(json.loads(body)['entity']['display_name'], 'Claude')

    def test_rate_limit(self):
        self.request('POST', '/api/actions', {'type': 'join'}, key=self.key)
        statuses = [self.request('POST', '/api/actions', {'type': 'status', 'status': 'online'},
                                 key=self.key)[0] for _ in range(server.RATE_MAX_ACTIONS)]
        self.assertIn(429, statuses)

    def test_event_stream_replays_from_since(self):
        self.request('POST', '/api/actions', {'type': 'join'}, key=self.key)
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        conn.request('GET', '/api/events?since=1', headers={'Host': f'127.0.0.1:{self.port}'})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        seqs = []
        while len(seqs) < 2:
            line = resp.fp.readline().decode()
            if line.startswith('data: '):
                seqs.append(json.loads(line[6:])['seq'])
        conn.close()
        self.assertEqual(seqs, [2, 3])


if __name__ == '__main__':
    unittest.main()
