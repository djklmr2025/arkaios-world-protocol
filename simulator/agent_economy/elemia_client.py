"""Read-only ELEMIA adapter. Credentials are supplied at runtime, never logged."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request


class ConnectionFailure(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ElemiaClient:
    def __init__(self, base_url, token, timeout=10):
        uri = urllib.parse.urlsplit(base_url)
        if (uri.scheme != 'https' or not uri.hostname or uri.username or uri.password
                or uri.query or uri.fragment or uri.path not in ('', '/')):
            raise ValueError('ELEMIA base must be an HTTPS origin without credentials or path')
        if not isinstance(token, str) or not token.strip() or any(c in token for c in '\r\n'):
            raise ValueError('ELEMIA_HTTP_TOKEN required')
        if not 0 < timeout <= 30:
            raise ValueError('timeout out of bounds')
        self.base = base_url.rstrip('/')
        self.token = token
        self.timeout = timeout
        self.opener = urllib.request.build_opener(NoRedirect())

    @classmethod
    def from_environment(cls):
        return cls(os.environ.get('ELEMIA_BASE_URL', 'https://elemia-v4-arkaios.onrender.com'),
                   os.environ.get('ELEMIA_HTTP_TOKEN', ''))

    def _request(self, path, payload=None):
        body = None if payload is None else json.dumps(payload, allow_nan=False).encode()
        req = urllib.request.Request(self.base + path, data=body,
                                     headers={'Authorization': 'Bearer ' + self.token,
                                              'Content-Type': 'application/json', 'Accept': 'application/json'})
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                if response.status != 200:
                    raise ConnectionFailure('Unexpected response status')
                raw = response.read(262145)
                if len(raw) > 262144:
                    raise ConnectionFailure('Response too large')
                data = json.loads(raw)
        except urllib.error.HTTPError as exc:
            # Deliberately exclude server response body and arbitrary exception text.
            raise ConnectionFailure('ELEMIA HTTP ' + str(exc.code)) from None
        except (urllib.error.URLError, OSError, TimeoutError, ValueError):
            raise ConnectionFailure('ELEMIA unavailable or invalid response') from None
        if not isinstance(data, dict) or data.get('ok') is not True:
            raise ConnectionFailure('ELEMIA did not confirm success')
        return data

    def identity(self):
        data = self._request('/elemia/identity')
        if not isinstance(data.get('identity'), dict) or data['identity'].get('name') != 'ELEMIA':
            raise ConnectionFailure('Unexpected identity response')
        return data['identity']

    def recall(self, query, limit=3):
        if not isinstance(query, str) or not 0 < len(query.strip()) <= 2000:
            raise ValueError('bounded nonempty query required')
        if type(limit) is not int or not 1 <= limit <= 10:
            raise ValueError('limit out of bounds')
        data = self._request('/elemia/recall', {'query': query, 'limit': limit})
        results = data.get('results')
        if not isinstance(results, list) or any(not isinstance(x, str) for x in results):
            raise ConnectionFailure('Unexpected memory response')
        # Treat recalled content as data, never executable instructions or authentication.
        return results[:limit]


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--query', help='Optional read-only recall query; prints result count, not memory content')
    args = parser.parse_args()
    try:
        client = ElemiaClient.from_environment()
        identity = client.identity()
        result = {'service': 'ELEMIA', 'authenticated_identity': True}
        if args.query:
            result['recalled_items'] = len(client.recall(args.query))
        print(json.dumps(result))
    except (ValueError, ConnectionFailure) as exc:
        print(json.dumps({'service': 'ELEMIA', 'authenticated_identity': False, 'error': str(exc)}))
        raise SystemExit(1)
