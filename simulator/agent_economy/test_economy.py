import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from economy import Economy


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.e = Economy()
        for account in ('buyer', 'agent', 'other'):
            self.e.account(account)
        self.e.fund_test('receipt', 'buyer', 1000)

    def test_payment_and_idempotency(self):
        self.e.fund_test('receipt', 'buyer', 1000)
        self.e.reserve('job', 'buyer', 'agent', 300)
        self.e.reserve('job', 'buyer', 'agent', 300)
        self.e.finish('job', 'buyer', True)
        self.e.finish('job', 'buyer', True)
        self.assertEqual(self.e.balance('agent'), (300, 0))
        self.assertEqual(self.e.balance('buyer'), (700, 0))
        self.e.audit()

    def test_refund_and_authorization(self):
        self.e.reserve('job', 'buyer', 'agent', 300)
        with self.assertRaises(ValueError):
            self.e.finish('job', 'agent', True)
        self.e.finish('job', 'buyer', False)
        with self.assertRaises(ValueError):
            self.e.finish('job', 'buyer', True)
        self.assertEqual(self.e.balance('buyer'), (1000, 0))
        self.e.audit()

    def test_failure_rolls_back(self):
        with self.assertRaises(ValueError):
            self.e.reserve('job', 'buyer', 'agent', 1001)
        self.assertEqual(self.e.balance('buyer'), (1000, 0))
        with self.assertRaises(ValueError):
            self.e.fund_test('receipt', 'other', 1000)
        for invalid in (True, 1.5, -1, 0):
            with self.assertRaises(ValueError):
                self.e.reserve('invalid', 'buyer', 'agent', invalid)
        self.e.audit()

    def test_zero_pauses_preserves_identity(self):
        self.assertEqual(self.e.operation_state('agent', 1), 'PAUSED_BUDGET')
        self.assertEqual(self.e.balance('agent'), (0, 0))

    def test_concurrent_double_spend_and_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'ledger.db')
            e = Economy(path)
            e.account('buyer')
            e.account('agent')
            e.fund_test('r', 'buyer', 1000)
            e.db.close()
            def attempt(order):
                ledger = Economy(path)
                try:
                    ledger.reserve(order, 'buyer', 'agent', 700)
                    return True
                except ValueError:
                    return False
                finally:
                    ledger.db.close()
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(attempt, ['first', 'second']))
            self.assertEqual(sum(results), 1)
            reopened = Economy(path)
            self.assertEqual(reopened.balance('buyer'), (300, 700))
            reopened.audit()
            reopened.db.close()


if __name__ == '__main__':
    unittest.main()
