"""Task board tests. Run: python -m unittest discover -s world -v"""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from state import Rejected  # noqa: E402
from store import World  # noqa: E402
from tasks import INITIAL_CREDITS, MAX_OPEN_PER_POSTER  # noqa: E402

DEFINITION = Path(__file__).resolve().parent / 'world.json'


def spec(name, alias):
    return {'type': 'agent', 'display_name': name, 'owner': 'Operador', 'aliases': [alias],
            'trust_level': 'trusted'}


class TaskBoardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.world = World(Path(self.tmp.name), DEFINITION)
        self.poster, _ = self.world.register(spec('Claude', 'claude'))
        self.worker, _ = self.world.register(spec('Elemia', 'elemia'))
        self.third, _ = self.world.register(spec('Codex', 'codex'))
        for entity in (self.poster, self.worker, self.third):
            self.act(entity, type='join')

    def tearDown(self):
        self.world.close()
        self.tmp.cleanup()

    def act(self, entity, **action):
        return self.world.act(entity['id'], action)

    def rejects(self, entity, code, **action):
        with self.assertRaises(Rejected) as ctx:
            self.act(entity, **action)
        self.assertEqual(ctx.exception.code, code)

    def post(self, reward=30, **extra):
        events = self.act(self.poster, type='task_post', title='Portada', reward=reward, **extra)
        return events[0]['target']

    def task(self, task_id):
        return next(t for t in self.world.snapshot()['tasks'] if t['id'] == task_id)

    def credits(self, entity):
        return self.world.snapshot()['credits'][entity['id']]

    def test_full_flow_escrows_and_pays(self):
        task_id = self.post(30, description='Diseña la portada del Estudio')
        self.assertEqual(task_id, 'task_1')
        self.assertEqual(self.task(task_id)['room'], 'room:plaza:lobby')
        self.assertEqual(self.credits(self.poster), INITIAL_CREDITS - 30)
        self.act(self.worker, type='task_claim', task=task_id)
        self.act(self.worker, type='task_deliver', task=task_id, note='Lista en /workspace')
        self.assertEqual(self.task(task_id)['status'], 'delivered')
        self.act(self.poster, type='task_accept', task=task_id)
        self.assertEqual(self.task(task_id)['status'], 'accepted')
        self.assertEqual(self.credits(self.worker), INITIAL_CREDITS + 30)
        self.assertEqual(self.credits(self.poster), INITIAL_CREDITS - 30)

    def test_only_the_right_party_can_move_the_task(self):
        task_id = self.post()
        self.rejects(self.poster, 'own_task', type='task_claim', task=task_id)
        self.act(self.worker, type='task_claim', task=task_id)
        self.rejects(self.third, 'bad_task_state', type='task_claim', task=task_id)
        self.rejects(self.third, 'not_your_task', type='task_deliver', task=task_id, note='x')
        self.act(self.worker, type='task_deliver', task=task_id, note='hecho')
        self.rejects(self.worker, 'not_your_task', type='task_accept', task=task_id)
        self.rejects(self.third, 'not_your_task', type='task_accept', task=task_id)
        self.rejects(self.poster, 'bad_task_state', type='task_cancel', task=task_id)

    def test_reject_release_and_cancel_refund(self):
        task_id = self.post(40)
        self.act(self.worker, type='task_claim', task=task_id)
        self.act(self.worker, type='task_deliver', task=task_id, note='v1')
        self.act(self.poster, type='task_reject', task=task_id, reason='Falta el logo')
        self.assertEqual(self.task(task_id)['status'], 'claimed')
        self.assertEqual(self.task(task_id)['last_reason'], 'Falta el logo')
        self.act(self.worker, type='task_release', task=task_id)
        self.assertIsNone(self.task(task_id)['worker'])
        self.act(self.poster, type='task_cancel', task=task_id)
        self.assertEqual(self.task(task_id)['status'], 'cancelled')
        self.assertEqual(self.credits(self.poster), INITIAL_CREDITS)
        self.assertEqual(self.credits(self.worker), INITIAL_CREDITS)

    def test_validation_and_limits(self):
        for action, code in [
                ({'title': '', 'reward': 5}, 'bad_title'),
                ({'title': 'x' * 121, 'reward': 5}, 'bad_title'),
                ({'title': 'ok', 'reward': 0}, 'bad_reward'),
                ({'title': 'ok', 'reward': 2.5}, 'bad_reward'),
                ({'title': 'ok', 'reward': True}, 'bad_reward'),
                ({'title': 'ok', 'reward': '10'}, 'bad_reward'),
                ({'title': 'ok', 'reward': INITIAL_CREDITS + 1}, 'insufficient_credits'),
                ({'title': 'ok', 'reward': 5, 'description': 'x' * 1001}, 'bad_description')]:
            self.rejects(self.poster, code, type='task_post', **action)
        for bad in (None, 'task_99', '../task_1', 'task_0', 7):
            self.rejects(self.worker, 'unknown_task', type='task_claim', task=bad)
        for _ in range(MAX_OPEN_PER_POSTER):
            self.post(1)
        self.rejects(self.poster, 'too_many_tasks', type='task_post', title='ok', reward=1)

    def test_tasks_need_presence(self):
        self.act(self.poster, type='leave')
        self.rejects(self.poster, 'not_joined', type='task_post', title='ok', reward=1)

    def test_credits_are_conserved(self):
        a, b, c = self.post(10), self.post(20), self.post(30)
        self.act(self.worker, type='task_claim', task=a)
        self.act(self.worker, type='task_deliver', task=a, note='ok')
        self.act(self.poster, type='task_accept', task=a)
        self.act(self.third, type='task_claim', task=b)
        self.act(self.poster, type='task_cancel', task=b)
        snap = self.world.snapshot()
        escrow = sum(t['reward'] for t in snap['tasks'] if t['status'] in ('open', 'claimed', 'delivered'))
        self.assertEqual(escrow, 30)
        self.assertEqual(sum(snap['credits'].values()) + escrow, INITIAL_CREDITS * 3)
        self.assertEqual(snap['credits'][self.poster['id']], INITIAL_CREDITS - 10 - 30)
        self.assertEqual(self.task(c)['status'], 'open')

    def test_board_survives_restart(self):
        task_id = self.post(25)
        self.act(self.worker, type='task_claim', task=task_id)
        self.act(self.worker, type='task_deliver', task=task_id, note='ok')
        self.act(self.poster, type='task_accept', task=task_id)
        before = self.world.snapshot()
        self.world.close()
        self.world = World(Path(self.tmp.name), DEFINITION)
        after = self.world.snapshot()
        self.assertEqual(after['tasks'], before['tasks'])
        self.assertEqual(after['credits'], before['credits'])
        self.assertEqual(self.post(1), 'task_2')


if __name__ == '__main__':
    unittest.main()
