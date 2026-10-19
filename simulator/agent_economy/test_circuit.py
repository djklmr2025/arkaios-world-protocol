import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from circuit import Circuit, canonical, demo


MUSIC_ROOT = os.environ.get('MUSIC_STUDIO_ROOT')


@unittest.skipUnless(MUSIC_ROOT, 'Set MUSIC_STUDIO_ROOT to the pinned music checkout')
class CircuitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.c = Circuit(self.root)
        self.buyer, self.seller = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
        self.c.register('buyer', self.buyer)
        self.c.register('seller', self.seller)
        self.c.ledger.fund_test('r', 'buyer', 1000)
        self.c.remember('seller', {'task_preference': 'spatial-render'}, self.seller)
        self.c.request('job', 'buyer', 'seller', 250)

    def tearDown(self):
        self.c.db.close()
        self.tmp.cleanup()

    def render(self):
        return self.c.render('job', MUSIC_ROOT, self.seller)

    def sign(self):
        return self.buyer.sign(canonical(self.c.acceptance_payload('job'))).hex()

    def test_real_audio_and_restart(self):
        payload = self.render()
        self.assertEqual(payload['audio']['frames'], 66150)
        self.assertEqual(self.c.ledger.balance('seller'), (0, 0))
        self.c.accept('job', self.sign())
        self.c.db.close()
        self.c = Circuit(self.root)
        self.assertEqual(self.c.recall('seller')[0]['task_preference'], 'spatial-render')
        self.c.request('job', 'buyer', 'seller', 250)
        self.render()
        self.c.accept('job', self.sign())
        self.assertEqual(self.c.ledger.balance('seller'), (250, 0))
        self.assertEqual(self.c.ledger.balance('buyer'), (750, 0))
        self.c.ledger.audit()

    def test_modified_artifact_not_paid(self):
        self.render()
        audio = self.root / 'artifacts/job/delivery.wav'
        with audio.open('ab') as f:
            f.write(b'tamper')
        with self.assertRaisesRegex(ValueError, 'artifact modified'):
            self.c.acceptance_payload('job')
        self.assertEqual(self.c.ledger.balance('seller'), (0, 0))
        self.c.ledger.audit()

    def test_forged_acceptance_not_paid(self):
        self.render()
        forged = self.seller.sign(canonical(self.c.acceptance_payload('job'))).hex()
        with self.assertRaises(InvalidSignature):
            self.c.accept('job', forged)
        self.assertEqual(self.c.ledger.balance('buyer'), (750, 250))

    def test_identity_and_memory_tampering(self):
        with self.assertRaisesRegex(ValueError, 'identity key mismatch'):
            self.c.register('seller', self.buyer)
        self.c.db.execute("UPDATE memories SET payload='{}' WHERE agent='seller'")
        with self.assertRaisesRegex(ValueError, 'memory chain mismatch'):
            self.render()
        self.assertEqual(self.c.ledger.balance('seller'), (0, 0))

    def test_worker_failure_keeps_reservation_refundable(self):
        with patch('circuit.subprocess.run', side_effect=RuntimeError('worker failed')):
            with self.assertRaises(RuntimeError):
                self.render()
        self.assertEqual(self.c.task('job')['state'], 'RESERVED')
        self.c.ledger.finish('job', 'buyer', False)
        self.assertEqual(self.c.ledger.balance('buyer'), (1000, 0))
        self.c.ledger.audit()

    def test_recovery_after_settlement_before_task_commit(self):
        self.render()
        signature = self.sign()
        with patch.object(self.c, 'record_acceptance', side_effect=RuntimeError('simulated crash')):
            with self.assertRaises(RuntimeError):
                self.c.accept('job', signature)
        self.assertEqual(self.c.task('job')['state'], 'VERIFIED')
        self.c.db.close()
        self.c = Circuit(self.root)
        self.c.accept('job', signature)
        self.assertEqual(self.c.task('job')['state'], 'ACCEPTED')
        self.assertEqual(self.c.ledger.balance('seller'), (250, 0))
        self.c.ledger.audit()

    def test_task_mismatch_and_path_rejection(self):
        with self.assertRaisesRegex(ValueError, 'task payload mismatch'):
            self.c.request('job', 'buyer', 'seller', 251)
        with self.assertRaisesRegex(ValueError, 'invalid local identifier'):
            self.c.request('../escape', 'buyer', 'seller', 1)
        self.c.ledger.audit()

    def test_persistent_demo_does_not_refund_or_repay(self):
        root = self.root / 'demo'
        first = demo(root, MUSIC_ROOT)
        second = demo(root, MUSIC_ROOT)
        self.assertEqual(first['agent_balance'], second['agent_balance'])
        self.assertGreater(second['recovered_memories'], 0)
        self.assertEqual(second['task'], 'ACCEPTED')


if __name__ == '__main__':
    unittest.main()
