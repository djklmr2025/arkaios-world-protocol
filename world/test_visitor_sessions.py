import unittest

from visitor_sessions import VisitorSessions


class VisitorSessionTests(unittest.TestCase):
    def setUp(self):
        self.sessions = VisitorSessions(secret=b'unit-test-secret', lifetime_s=60)

    def test_issues_and_verifies_a_short_lived_session(self):
        token = self.sessions.issue('google-subject', 'Ana')
        self.assertEqual(self.sessions.verify(token), {'sub': 'google-subject', 'name': 'Ana'})

    def test_rejects_a_tampered_session(self):
        token = self.sessions.issue('google-subject', 'Ana')
        self.assertIsNone(self.sessions.verify(token + 'x'))
