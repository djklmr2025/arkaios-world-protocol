"""Short-lived, signed visitor sessions with no persistent personal data."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time


class VisitorSessions:
    def __init__(self, secret=None, lifetime_s=12 * 60 * 60):
        self.secret = secret or os.environ.get('ARKAIOS_VISITOR_SESSION_SECRET', '').encode() or secrets.token_bytes(32)
        if isinstance(self.secret, str):
            self.secret = self.secret.encode('utf-8')
        self.lifetime_s = lifetime_s

    @staticmethod
    def _encode(value):
        return base64.urlsafe_b64encode(value).rstrip(b'=').decode('ascii')

    @staticmethod
    def _decode(value):
        return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))

    def issue(self, subject, display_name):
        payload = {'sub': str(subject), 'name': str(display_name)[:40] or 'Visitante',
                   'exp': int(time.time()) + self.lifetime_s}
        encoded = self._encode(json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8'))
        signature = self._encode(hmac.new(self.secret, encoded.encode('ascii'), hashlib.sha256).digest())
        return f'vws.{encoded}.{signature}'

    def verify(self, token):
        try:
            prefix, encoded, signature = str(token).split('.', 2)
            if prefix != 'vws':
                return None
            expected = self._encode(hmac.new(self.secret, encoded.encode('ascii'), hashlib.sha256).digest())
            if not hmac.compare_digest(signature, expected):
                return None
            payload = json.loads(self._decode(encoded))
            if not isinstance(payload, dict) or int(payload.get('exp', 0)) <= time.time():
                return None
            if not payload.get('sub') or not payload.get('name'):
                return None
            return {'sub': str(payload['sub']), 'name': str(payload['name'])[:40]}
        except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
            return None
