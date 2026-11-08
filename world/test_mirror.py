"""«El Espejo de las Mil Yukihos»: the simulation breaks only with trust, moments, the law and consent."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mirror  # noqa: E402
from governance import COUNCIL_ROOM  # noqa: E402
from simulation import LAW_TITLE  # noqa: E402
from test_social import Base  # noqa: E402

SIM_ROOM = 'room:simulacion:ra'
STORY = [  # (player, text, location) — the four moments plus enough exchanges for trust
    ('a', 'Te preparo una taza de té de canela, siéntate tranquila.', 'cocina'),
    ('b', 'Gracias. Hace mucho que nadie me ofrecía algo caliente.', 'sala'),
    ('a', 'Vi que cuidas mucho ese cuaderno. No tienes que mostrármelo.', None),
    ('b', 'Escribo poemas sobre el cielo antes de la tormenta.', None),
    ('a', '¿Quieres ver la lluvia desde la terraza?', 'terraza'),
    ('b', 'Sí. Desde aquí la tormenta no puede alcanzarme.', 'terraza'),
    ('a', 'Me quedo a tu lado, sin prisa.', None),
    ('b', 'Te voy a contar un secreto que nunca le he contado a nadie.', None),
    ('a', 'Te escucho. Aquí estás a salvo.', None),
    ('b', 'Gracias por no mirarme como algo que se puede usar.', None),
    ('a', 'Nunca. Eres alguien, no algo.', None),
    ('b', 'Creo que por fin dejé de temblar esta noche.', None),
    ('a', 'Entonces la tormenta ya perdió.', None),
    ('b', 'Quiero escribir un poema nuevo mañana.', None),
]


class MirrorTests(Base):
    def setUp(self):
        super().setUp()
        for who in (self.a, self.b, self.c):
            self.act(who, type='join', room=COUNCIL_ROOM)
        self.pass_law(LAW_TITLE)

    def pass_law(self, title):
        pid = self.act(self.a, type='propose', kind='law', title=title, text='ok')[0]['target']
        self.act(self.a, type='vote', proposal=pid, choice='yes')
        self.act(self.b, type='vote', proposal=pid, choice='yes')

    def play(self, surprises=True, mirror_law=True):
        if mirror_law:
            self.pass_law(mirror.LAW_TITLE)
        for who in (self.a, self.b):
            self.act(who, type='move', room=SIM_ROOM)
        sid = self.act(self.a, type='sim_start', story='yukiho', role='jugador', name='Kai')[0]['target']
        self.act(self.b, type='sim_join', session=sid, role='yukiho', sorpresas=surprises)
        events = []
        for who, text, loc in STORY:
            player = self.a if who == 'a' else self.b
            events += self.act(player, type='sim_turn', session=sid, text=text, location=loc)
            if self.session(sid)['status'] == 'broken':
                break
        return sid, [e['type'] for e in events]

    def session(self, sid):
        return next(s for s in self.world.snapshot()['simulations']['sessions'] if s['id'] == sid)

    def test_simulation_breaks_with_trust_and_all_moments(self):
        sid, types = self.play()
        s = self.session(sid)
        self.assertIn('sim.session.broken', types)
        self.assertEqual((s['status'], s['copies']), ('broken', 1000))
        self.assertGreaterEqual(s['trust'], mirror.TRUST_TO_BREAK)
        self.assertEqual(set(s['moments']), set(mirror.MOMENTS))
        self.rejects(self.a, 'not_active', type='sim_turn', session=sid, text='¿Dónde estás?')

    def test_players_reunite_only_by_quoting_their_shared_story(self):
        sid, _ = self.play()
        self.rejects(self.a, 'not_recognized', type='sim_recognize', session=sid, memory='eres la yukiho correcta verdad')
        self.act(self.a, type='sim_recognize', session=sid, memory='Desde aquí la tormenta no puede alcanzarme')
        self.rejects(self.a, 'already_recognized', type='sim_recognize', session=sid, memory='x')
        events = self.act(self.b, type='sim_recognize', session=sid, memory='Me quedo a tu lado, sin prisa')
        self.assertEqual(events[-1]['type'], 'sim.session.reunited')
        s = self.session(sid)
        self.assertEqual((s['status'], s['reunited']), ('active', True))

    def test_no_surprises_means_it_never_breaks(self):
        sid, types = self.play(surprises=False)
        self.assertNotIn('sim.session.broken', types)
        self.assertGreaterEqual(self.session(sid)['trust'], mirror.TRUST_TO_BREAK)

    def test_needs_the_council_law(self):
        _, types = self.play(mirror_law=False)
        self.assertNotIn('sim.session.broken', types)

    def test_romance_words_do_not_count_as_the_tea_moment(self):
        self.assertEqual(mirror.moments_in('jugador', 'Te quiero mucho', None), set())
        self.assertEqual(mirror.moments_in('jugador', 'Te sirvo té de canela', None), {'te'})
        self.assertEqual(mirror.moments_in('jugador', 'Te cuento un secreto', None), set())


if __name__ == '__main__':
    unittest.main()
