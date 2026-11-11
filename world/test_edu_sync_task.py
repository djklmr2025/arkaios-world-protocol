"""Scheduled sync task tests. Run: python -m unittest discover -s world -v"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import edu_sync_task as task  # noqa: E402


class WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = mock.patch.object(task, 'LOG', Path(self.tmp.name) / 'edu-sync.log')
        self.log.start()
        self.sleep = mock.patch.object(task.time, 'sleep', lambda s: None)
        self.sleep.start()

    def tearDown(self):
        self.sleep.stop()
        self.log.stop()
        self.tmp.cleanup()

    def test_world_already_up_is_left_alone(self):
        with mock.patch.object(task, 'world_up', return_value=True), \
                mock.patch.object(task, 'start_world') as start:
            self.assertTrue(task.ensure_world())
        start.assert_not_called()

    def test_world_down_is_started_and_waited_for(self):
        answers = iter([False, False, True])
        with mock.patch.object(task, 'world_up', lambda: next(answers)), \
                mock.patch.object(task, 'start_world') as start:
            self.assertTrue(task.ensure_world())
        start.assert_called_once()
        self.assertIn('arrancándolo', task.LOG.read_text(encoding='utf-8'))

    def test_world_that_never_comes_up_is_reported_and_sync_skipped(self):
        with mock.patch.object(task, 'world_up', return_value=False), \
                mock.patch.object(task, 'start_world'), \
                mock.patch.object(task, 'sync_requests') as sync:
            self.assertEqual(task.main(), 0)
        sync.assert_not_called()
        self.assertIn('sigue sin responder', task.LOG.read_text(encoding='utf-8'))

    def test_errors_are_logged_not_raised(self):
        with mock.patch.object(task, 'world_up', return_value=True), \
                mock.patch.object(task, 'sync_requests', side_effect=OSError('sin red')):
            self.assertEqual(task.main(), 1)
        self.assertIn('sin red', task.LOG.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
