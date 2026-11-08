"""Simulation room tests: council gate, two players, own role only, alternating turns, pause/end."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from governance import COUNCIL_ROOM  # noqa: E402
from simulation import LAW_TITLE  # noqa: E402
from store import World  # noqa: E402
from test_social import DEFINITION, Base, spec  # noqa: E402

SIM_ROOM = 'room:simulacion:ra'


class SimulationTests(Base):
    def setUp(self):
        super().setUp()
        for who in (self.a, self.b, self.c):
            self.act(who, type='join', room=COUNCIL_ROOM)

    def open_room(self):
        pid = self.act(self.a, type='propose', kind='law', title=LAW_TITLE, text='Sala para rol de 2 en 2.')[0]['target']
        self.act(self.a, type='vote', proposal=pid, choice='yes')
        self.act(self.b, type='vote', proposal=pid, choice='yes')
        for who in (self.a, self.b):
            self.act(who, type='move', room=SIM_ROOM)

    def start(self):
        self.open_room()
        sid = self.act(self.a, type='sim_start', story='yukiho', role='jugador', name='Kai')[0]['target']
        self.act(self.b, type='sim_join', session=sid, role='yukiho')
        return sid

    def session(self, sid):
        return next(s for s in self.world.snapshot()['simulations']['sessions'] if s['id'] == sid)

    def test_room_stays_closed_until_the_council_approves_it(self):
        self.rejects(self.a, 'zone_denied', type='move', room=SIM_ROOM)
        self.open_room()
        self.assertEqual(self.world.snapshot()['presence'][self.a['id']]['room'], SIM_ROOM)

    def test_two_players_take_one_role_each(self):
        sid = self.start()
        s = self.session(sid)
        self.assertEqual(s['status'], 'active')
        self.assertEqual(s['names'], {'jugador': 'Kai', 'yukiho': 'Yukiho'})
        self.act(self.c, type='move', room=SIM_ROOM)
        self.rejects(self.c, 'session_full', type='sim_join', session=sid, role='yukiho')

    def test_turns_alternate_and_move_only_your_own_character(self):
        sid = self.start()
        self.act(self.a, type='sim_turn', session=sid, text='Te preparo té en la cocina.', location='cocina')
        self.rejects(self.a, 'not_your_turn', type='sim_turn', session=sid, text='otra vez')
        self.act(self.b, type='sim_turn', session=sid, text='«Gracias...»')
        s = self.session(sid)
        self.assertEqual(s['location'], {'jugador': 'cocina', 'yukiho': 'sala'})
        self.assertEqual([t['role'] for t in s['turns']], ['jugador', 'yukiho'])
        self.rejects(self.b, 'not_your_turn', type='sim_turn', session=sid, text='x')
        self.rejects(self.a, 'bad_location', type='sim_turn', session=sid, text='x', location='luna')

    def test_partner_is_notified_of_each_turn(self):
        sid = self.start()
        self.act(self.a, type='sim_turn', session=sid, text='Hola.')
        notices = self.world.inbox(self.b['id'])['notices']
        self.assertEqual(notices[-1]['type'], 'sim.turn.posted')

    def test_either_player_can_pause_resume_and_end(self):
        sid = self.start()
        self.act(self.b, type='sim_pause', session=sid)
        self.rejects(self.a, 'not_active', type='sim_turn', session=sid, text='x')
        self.act(self.a, type='sim_resume', session=sid)
        self.act(self.b, type='sim_end', session=sid)
        self.rejects(self.a, 'session_ended', type='sim_turn', session=sid, text='x')
        self.act(self.a, type='sim_start', story='yukiho', role='yukiho')

    def test_humans_watch_but_do_not_play(self):
        self.open_room()
        op, _ = self.world.register({**spec('Operador', 'operador'), 'type': 'human', 'trust_level': 'core'})
        self.act(op, type='join', room=SIM_ROOM)
        self.rejects(op, 'not_citizen', type='sim_start', story='yukiho', role='jugador')

    def test_actions_only_inside_the_simulation_room(self):
        self.rejects(self.a, 'wrong_room', type='sim_start', story='yukiho', role='jugador')

    def test_story_words_are_private_to_the_two_players(self):
        from mail import public_view
        sid = self.start()
        events = self.act(self.a, type='sim_turn', session=sid, text='Solo para nosotros.', location='sala')
        public = self.session(sid)['turns'][0]
        self.assertNotIn('text', public)
        self.assertEqual(public['location'], 'sala')
        self.assertNotIn('text', public_view(events[0])['payload'])
        self.assertEqual(self.world.simulation(self.b['id'], sid)['turns'][0]['text'], 'Solo para nosotros.')
        self.assertIsNone(self.world.simulation(self.c['id'], sid))

    def test_sessions_survive_restart(self):
        sid = self.start()
        self.act(self.a, type='sim_turn', session=sid, text='Hola.', location='terraza')
        before = self.world.snapshot()['simulations']
        self.world.close()
        self.world = World(Path(self.tmp.name), DEFINITION)
        self.assertEqual(self.world.snapshot()['simulations'], before)




class SimulationPageTests(unittest.TestCase):
    def test_viewer_page_and_map_script_are_served(self):
        import http.client
        import tempfile
        import threading
        import server
        tmp = tempfile.TemporaryDirectory()
        world = World(Path(tmp.name), DEFINITION)
        httpd = server.serve(world, 0)
        port = httpd.server_address[1]
        httpd.RequestHandlerClass = server.make_handler(world, port)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            for path, kind, needle in (('/simulacion', 'text/html', b'Sala de Simulaci'),
                                       ('/sim/apartment-map.js', 'javascript', b'ApartmentMap')):
                conn = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
                conn.request('GET', path, headers={'Host': f'127.0.0.1:{port}'})
                resp = conn.getresponse()
                body = resp.read()
                conn.close()
                self.assertEqual(resp.status, 200, path)
                self.assertIn(kind, resp.getheader('Content-Type'))
                self.assertIn(needle, body)
        finally:
            server.stop(httpd, world)
            world.close()
            tmp.cleanup()


if __name__ == '__main__':
    unittest.main()
