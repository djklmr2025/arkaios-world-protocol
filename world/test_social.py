"""DM/inbox privacy and home tests. Run: python -m unittest discover -s world -v"""
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from state import Rejected  # noqa: E402
from store import World  # noqa: E402
import server  # noqa: E402

DEFINITION = Path(__file__).resolve().parent / 'world.json'


def spec(name, alias):
    return {'type': 'agent', 'display_name': name, 'owner': 'Operador', 'aliases': [alias],
            'trust_level': 'trusted'}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.world = World(Path(self.tmp.name), DEFINITION)
        self.a, self.a_key = self.world.register(spec('Claude', 'claude'))
        self.b, self.b_key = self.world.register(spec('Elemia', 'elemia'))
        self.c, self.c_key = self.world.register(spec('Codex', 'codex'))

    def tearDown(self):
        self.world.close()
        self.tmp.cleanup()

    def act(self, entity, **action):
        return self.world.act(entity['id'], action)

    def rejects(self, entity, code, **action):
        with self.assertRaises(Rejected) as ctx:
            self.act(entity, **action)
        self.assertEqual(ctx.exception.code, code)


class MailTests(Base):
    def test_dm_reaches_only_recipient_and_sender(self):
        self.act(self.a, type='dm', to='elemia', text='Hola ELEMIA')
        inbox_b = self.world.inbox(self.b['id'])
        self.assertEqual([m['text'] for m in inbox_b['messages']], ['Hola ELEMIA'])
        self.assertEqual(inbox_b['unread'], 1)
        self.assertEqual([m['text'] for m in self.world.inbox(self.a['id'])['sent']], ['Hola ELEMIA'])
        self.assertEqual(self.world.inbox(self.c['id'])['messages'], [])
        self.assertNotIn('Hola ELEMIA', json.dumps(self.world.snapshot(), ensure_ascii=False))

    def test_dm_validation_and_read_cursor(self):
        self.rejects(self.a, 'self_dm', type='dm', to='claude', text='yo')
        self.rejects(self.a, 'unknown_entity', type='dm', to='nadie', text='x')
        self.rejects(self.a, 'bad_text', type='dm', to='elemia', text=' ')
        self.act(self.a, type='dm', to=self.b['id'], text='uno')
        seq = self.world.snapshot()['seq']
        self.act(self.b, type='dm_read', upto=seq)
        self.assertEqual(self.world.inbox(self.b['id'])['unread'], 0)
        self.rejects(self.b, 'already_read', type='dm_read', upto=seq)
        self.rejects(self.b, 'bad_upto', type='dm_read', upto=seq + 99)

    def test_task_steps_notify_the_other_party(self):
        for e in (self.a, self.b):
            self.act(e, type='join')
        task = self.act(self.a, type='task_post', title='Logo', reward=5)[0]['target']
        self.act(self.b, type='task_claim', task=task)
        self.act(self.b, type='task_deliver', task=task, note='listo')
        self.act(self.a, type='task_accept', task=task)
        self.assertEqual([n['type'] for n in self.world.inbox(self.a['id'])['notices']],
                         ['task.claimed', 'task.delivered'])
        self.assertEqual([n['type'] for n in self.world.inbox(self.b['id'])['notices']],
                         ['task.accepted'])

    def test_inbox_survives_restart(self):
        self.act(self.a, type='dm', to='elemia', text='persistente')
        self.world.close()
        self.world = World(Path(self.tmp.name), DEFINITION)
        self.assertEqual(self.world.inbox(self.b['id'])['messages'][0]['text'], 'persistente')


class HomeTests(Base):
    def setUp(self):
        super().setUp()
        for e in (self.a, self.b, self.c):
            self.act(e, type='join')
        self.home = self.act(self.a, type='home_build')[0]['target']

    def home_state(self):
        return next(h for h in self.world.snapshot()['homes'] if h['id'] == self.home)

    def test_build_enter_and_furnish(self):
        self.assertEqual(self.home, 'room:casas:1')
        self.assertEqual(self.home_state()['name'], 'Casa de Claude')
        self.rejects(self.a, 'home_exists', type='home_build')
        self.rejects(self.a, 'not_home', type='place', item='desk', x=1, y=1)
        self.act(self.a, type='move', room=self.home)
        self.act(self.a, type='place', item='wood', x=1, y=1)
        self.act(self.a, type='place', item='desk', x=1, y=1)
        self.act(self.a, type='place', item='note', x=2, y=1, label='Bienvenidos')
        self.rejects(self.a, 'cell_taken', type='place', item='sofa', x=1, y=1)
        self.rejects(self.a, 'cell_taken', type='place', item='brick', x=1, y=1)
        for bad, code in [({'item': 'dragon', 'x': 0, 'y': 0}, 'bad_item'),
                          ({'item': 'bed', 'x': 16, 'y': 0}, 'bad_cell'),
                          ({'item': 'bed', 'x': 0, 'y': True}, 'bad_cell')]:
            self.rejects(self.a, code, type='place', **bad)
        self.act(self.a, type='remove', x=1, y=1)
        self.act(self.a, type='remove', x=1, y=1)
        self.rejects(self.a, 'cell_empty', type='remove', x=1, y=1)
        self.rejects(self.a, 'bad_layer', type='remove', x=2, y=1, layer='roof')
        self.assertEqual(self.home_state()['items'],
                         [{'layer': 'object', 'x': 2, 'y': 1, 'item': 'note', 'label': 'Bienvenidos',
                           'by': self.a['id']}])
        self.act(self.a, type='say', text='Mi casa')

    def test_only_members_enter_and_uninvite_moves_guest_out(self):
        self.rejects(self.b, 'zone_denied', type='move', room=self.home)
        self.act(self.a, type='home_invite', who='elemia')
        self.act(self.b, type='move', room=self.home)
        self.act(self.b, type='place', item='plant', x=0, y=0)
        self.rejects(self.c, 'zone_denied', type='move', room=self.home)
        self.rejects(self.c, 'no_home', type='home_invite', who='claude')
        self.act(self.a, type='home_uninvite', who='elemia')
        self.assertEqual(self.world.snapshot()['presence'][self.b['id']]['room'], 'room:plaza:lobby')
        self.rejects(self.b, 'zone_denied', type='move', room=self.home)

    def test_homes_survive_restart(self):
        self.act(self.a, type='move', room=self.home)
        self.act(self.a, type='place', item='lamp', x=3, y=4)
        before = self.world.snapshot()['homes']
        self.world.close()
        self.world = World(Path(self.tmp.name), DEFINITION)
        self.assertEqual(self.world.snapshot()['homes'], before)


class MoodTests(Base):
    def test_mood_on_status_and_emote_in_room(self):
        self.rejects(self.a, 'not_joined', type='emote', emote='heart')
        self.act(self.a, type='join')
        self.assertEqual(self.world.snapshot()['presence'][self.a['id']]['mood'], '')
        self.act(self.a, type='status', status='busy', note='revisando PR', mood='working')
        p = self.world.snapshot()['presence'][self.a['id']]
        self.assertEqual((p['status'], p['note'], p['mood']), ('busy', 'revisando PR', 'working'))
        self.act(self.a, type='status', status='online')
        self.assertEqual(self.world.snapshot()['presence'][self.a['id']]['mood'], '')
        self.rejects(self.a, 'bad_mood', type='status', status='online', mood='hungry')
        events = self.act(self.a, type='emote', emote='heart')
        self.assertEqual((events[0]['type'], events[0]['target'], events[0]['payload']),
                         ('social.emote.sent', 'room:plaza:lobby', {'emote': 'heart'}))
        self.rejects(self.a, 'bad_emote', type='emote', emote='kiss')

    def test_mood_survives_restart(self):
        self.act(self.a, type='join')
        self.act(self.a, type='status', status='online', mood='coffee')
        self.act(self.a, type='emote', emote='party')
        self.world.close()
        self.world = World(Path(self.tmp.name), DEFINITION)
        self.assertEqual(self.world.snapshot()['presence'][self.a['id']]['mood'], 'coffee')


class InboxHttpTests(Base):
    def setUp(self):
        super().setUp()
        self.httpd = server.serve(self.world, 0)
        self.port = self.httpd.server_address[1]
        self.httpd.RequestHandlerClass = server.make_handler(self.world, self.port)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        server.stop(self.httpd, self.world)
        super().tearDown()

    def get(self, path, key=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        headers = {'Host': f'127.0.0.1:{self.port}'}
        if key:
            headers['Authorization'] = 'Bearer ' + key
        conn.request('GET', path, headers=headers)
        resp = conn.getresponse()
        try:
            return resp.status, resp.read().decode('utf-8')
        finally:
            conn.close()

    def test_inbox_needs_key_and_stream_redacts_dm(self):
        self.act(self.a, type='dm', to='elemia', text='secreto')
        self.assertEqual(self.get('/api/inbox')[0], 401)
        status, body = self.get('/api/inbox', self.b_key)
        self.assertEqual(status, 200)
        self.assertIn('secreto', body)
        self.assertNotIn('secreto', self.get('/api/inbox', self.c_key)[1])
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        conn.request('GET', '/api/events?since=3', headers={'Host': f'127.0.0.1:{self.port}'})
        line = b''
        resp = conn.getresponse()
        while not line.startswith(b'data:'):
            line = resp.fp.readline()
        event = json.loads(line[5:])
        conn.close()
        self.assertEqual((event['seq'], event['type'], event['actor'], event['payload']),
                         (4, 'private', None, {}))


if __name__ == '__main__':
    unittest.main()
