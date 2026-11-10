"""Educación Libre -> task board bridge tests. Run: python -m unittest discover -s world -v"""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from edu_inbox_bridge import UNTRUSTED_NOTE, load_ledger, save_ledger, sync, to_task  # noqa: E402
from state import Rejected  # noqa: E402
from store import World  # noqa: E402
from tasks import MAX_DESCRIPTION, MAX_TITLE  # noqa: E402

DEFINITION = Path(__file__).resolve().parent / 'world.json'


def request(n, **extra):
    return {'id': f'task_edu_{n}', 'title': f'Plantilla {n}', 'grade': 'primaria',
            'author': 'Prof. Prueba', 'narration': 'Tabla de lunes a viernes.', 'file': None,
            'status': 'queued_for_claude', 'createdAt': f'2026-11-10T10:00:0{n}Z', **extra}


class WorldClient:
    """Speaks to a real in-process World the way the HTTP client would."""

    def __init__(self, world, entity):
        self.world, self.entity = world, entity

    def act(self, **action):
        try:
            return {'ok': True, 'events': self.world.act(self.entity['id'], action)}
        except Rejected as exc:
            return {'ok': False, 'code': exc.code, 'message': exc.message}


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.world = World(Path(self.tmp.name), DEFINITION)
        claude, _ = self.world.register({'type': 'agent', 'display_name': 'Claude', 'owner': 'Operador',
                                         'aliases': ['claude'], 'trust_level': 'core'})
        self.client = WorldClient(self.world, claude)

    def tearDown(self):
        self.world.close()
        self.tmp.cleanup()

    def board(self):
        return self.world.snapshot()['tasks']

    def test_posts_new_requests_oldest_first_and_joins_if_needed(self):
        result = sync([request(2), request(1)], self.client, {})
        self.assertIsNone(result['error'])
        self.assertEqual([p[0] for p in result['posted']], ['task_edu_1', 'task_edu_2'])
        titles = [t['title'] for t in self.board()]
        self.assertEqual(titles, ['Plantilla: Plantilla 1', 'Plantilla: Plantilla 2'])
        self.assertTrue(self.board()[0]['description'].startswith(UNTRUSTED_NOTE))

    def test_rerun_with_ledger_does_not_duplicate(self):
        first = sync([request(1)], self.client, {})
        second = sync([request(1), request(2)], self.client, first['ledger'])
        self.assertEqual([p[0] for p in second['posted']], ['task_edu_2'])
        self.assertEqual(len(self.board()), 2)

    def test_skips_invalid_or_finished_requests(self):
        items = [request(1, id='../evil'), request(2, status='done'), request(3, narration=' '),
                 'not a dict', request(4)]
        result = sync(items, self.client, {})
        self.assertEqual([p[0] for p in result['posted']], ['task_edu_4'])
        self.assertEqual(result['skipped'], 3)

    def test_long_fields_fit_world_limits(self):
        action = to_task(request(1, title='T' * 500, narration='N' * 5000,
                                 file={'name': 'boceto.png', 'size': '1 MB'}))
        self.assertLessEqual(len(action['title']), MAX_TITLE)
        self.assertLessEqual(len(action['description']), MAX_DESCRIPTION)
        self.assertIn('boceto.png', action['description'])
        result = sync([request(1, title='T' * 500, narration='N' * 5000)], self.client, {})
        self.assertIsNone(result['error'])

    def test_stops_on_world_rejection_and_keeps_ledger_of_what_posted(self):
        class Refusing:
            def act(self, **action):
                return {'ok': False, 'code': 'insufficient_credits', 'message': 'no'}
        result = sync([request(1)], Refusing(), {'task_edu_0': 'task_9'})
        self.assertIn('insufficient_credits', result['error'])
        self.assertEqual(result['ledger'], {'task_edu_0': 'task_9'})

    def test_attachment_links_to_keyed_download(self):
        action = to_task(request(1, file={'id': '1AbCdEfGhIjK', 'name': 'libreta.jpg', 'size': 204800}))
        self.assertIn('libreta.jpg (200 KB)', action['description'])
        self.assertIn('?action=file&id=1AbCdEfGhIjK', action['description'])
        hostile = to_task(request(2, file={'id': '../../x?y=1', 'name': 'a.pdf', 'size': 1}))
        self.assertNotIn('action=file', hostile['description'])

    def test_dry_run_posts_nothing(self):
        result = sync([request(1)], self.client, {}, dry_run=True)
        self.assertEqual(len(result['posted']), 1)
        self.assertEqual(self.board(), [])
        self.assertEqual(result['ledger'], {})

    def test_ledger_round_trip(self):
        path = Path(self.tmp.name) / 'edu-inbox.json'
        self.assertEqual(load_ledger(path), {})
        save_ledger({'task_edu_1': 'task_1'}, path)
        self.assertEqual(load_ledger(path), {'task_edu_1': 'task_1'})


if __name__ == '__main__':
    unittest.main()
