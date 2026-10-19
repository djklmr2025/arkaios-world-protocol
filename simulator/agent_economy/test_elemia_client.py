import io
import json
import unittest
import urllib.error
from unittest.mock import patch
from elemia_client import ElemiaClient, ConnectionFailure, NoRedirect


class Response(io.BytesIO):
    status = 200


class ElemiaTests(unittest.TestCase):
    def setUp(self):
        self.c = ElemiaClient('https://example.invalid', 'test-only-not-real')

    def response(self, obj):
        return Response(json.dumps(obj).encode())

    def test_authenticated_identity_contract(self):
        with patch.object(self.c.opener, 'open', return_value=self.response({'ok': True, 'identity': {'name': 'ELEMIA'}})) as opened:
            self.assertEqual(self.c.identity()['name'], 'ELEMIA')
            request = opened.call_args.args[0]
            self.assertEqual(request.get_header('Authorization'), 'Bearer test-only-not-real')
            self.assertEqual(request.full_url, 'https://example.invalid/elemia/identity')

    def test_recall_contract_and_limits(self):
        with patch.object(self.c.opener, 'open', return_value=self.response({'ok': True, 'results': ['context']})) as opened:
            self.assertEqual(self.c.recall('task', 1), ['context'])
            self.assertEqual(json.loads(opened.call_args.args[0].data), {'query': 'task', 'limit': 1})
        with self.assertRaises(ValueError):
            self.c.recall('x', True)

    def test_errors_fail_closed_without_body(self):
        for obj in ({'ok': False}, {'ok': True, 'identity': 'fake'}, {'ok': True, 'identity': {'name': 'other'}}):
            with patch.object(self.c.opener, 'open', return_value=self.response(obj)):
                with self.assertRaises(ConnectionFailure):
                    self.c.identity()
        err = urllib.error.HTTPError('https://example.invalid', 401, 'sensitive-body', {}, None)
        with patch.object(self.c.opener, 'open', side_effect=err):
            with self.assertRaisesRegex(ConnectionFailure, '^ELEMIA HTTP 401$'):
                self.c.identity()

    def test_no_redirect_and_no_insecure_origin(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.invalid'))
        for url in ('http://example.invalid', 'https://user:pass@example.invalid', 'https://example.invalid?key=x'):
            with self.assertRaises(ValueError):
                ElemiaClient(url, 'test')
        with self.assertRaises(ValueError):
            ElemiaClient('https://example.invalid', '')

    def test_timeout_not_success(self):
        with patch.object(self.c.opener, 'open', side_effect=TimeoutError('private-data')):
            with self.assertRaisesRegex(ConnectionFailure, '^ELEMIA unavailable or invalid response$'):
                self.c.identity()


if __name__ == '__main__':
    unittest.main()
