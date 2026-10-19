"""Full pilot regression: preserve the chain on restart; reject altered audio."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from run_pilot import main


@unittest.skipUnless(os.environ.get('MUSIC_STUDIO_ROOT'), 'Set MUSIC_STUDIO_ROOT to the pinned music checkout')
class PilotTests(unittest.TestCase):
    def test_restart_and_tampered_audio_invalidates_success(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            first = main(root, os.environ['MUSIC_STUDIO_ROOT'])
            second = main(root, os.environ['MUSIC_STUDIO_ROOT'])
            self.assertEqual(first['testnet'], second['testnet'])
            self.assertTrue(second['verified_restart'])
            self.assertTrue((root / 'pilot-report.json').exists())
            audio = root / 'circuit/artifacts/render-001/delivery.wav'
            original = audio.read_bytes()
            audio.write_bytes(original[:-100])
            with self.assertRaises(subprocess.CalledProcessError):
                main(root, os.environ['MUSIC_STUDIO_ROOT'])
            self.assertFalse((root / 'pilot-report.json').exists())

    def test_bad_source_removes_previous_success_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / 'pilot-report.json'
            marker.write_text('{"verified_restart":true}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'music source mismatch'):
                main(root, root / 'missing-source')
            self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
