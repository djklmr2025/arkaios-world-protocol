"""ARKAIOS WORLD reference server v0.1 (loopback only, stdlib only).

  python world/server.py serve    --state DIR [--port 4300]
  python world/server.py register --state DIR --type agent --name Claude --alias claude \
                                  --owner "Operador ARKAIOS" --trust core [--capability coding]
  python world/server.py revoke   --state DIR --id ark:local-alpha:3 --reason "..."
  python world/server.py list     --state DIR

register/revoke/list need the server stopped (one writer per state dir).
The access key is printed once by `register`; only its SHA-256 is stored.
"""
import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import time
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from state import Rejected  # noqa: E402
from store import World  # noqa: E402

HERE = Path(__file__).resolve().parent
DEFAULT_DEFINITION = HERE / 'world.json'
CLIENT_HTML = HERE / 'client' / 'index.html'
LOOPBACK = '127.0.0.1'
MAX_BODY = 4096
RATE_WINDOW_S = 10.0
RATE_MAX_ACTIONS = 20
SSE_WAIT_S = 15.0


class RateLimiter:
    def __init__(self, window: float, limit: int):
        self.window, self.limit = window, limit
        self.hits = {}
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self.lock:
            recent = [t for t in self.hits.get(key, ()) if now - t < self.window]
            if len(recent) >= self.limit:
                self.hits[key] = recent
                return False
            self.hits[key] = recent + [now]
            return True


def make_handler(world: World, port: int):
    allowed_hosts = {f'{LOOPBACK}:{port}', f'localhost:{port}'}
    limiter = RateLimiter(RATE_WINDOW_S, RATE_MAX_ACTIONS)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'ArkaiosWorld/0.1'
        protocol_version = 'HTTP/1.1'

        def log_message(self, fmt, *args):
            sys.stderr.write('%s %s\n' % (self.log_date_time_string(), fmt % args))

        def _send_json(self, status: int, body: dict) -> None:
            data = json.dumps(body, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def _error(self, status: int, code: str, message: str) -> None:
            self._send_json(status, {'ok': False, 'error': code, 'message': message})

        def _host_ok(self) -> bool:
            # Blocks DNS-rebinding: browsers send the attacker's hostname here.
            if self.headers.get('Host') in allowed_hosts:
                return True
            self._error(HTTPStatus.FORBIDDEN, 'bad_host', 'loopback host required')
            return False

        def _auth(self):
            header = self.headers.get('Authorization', '')
            key = header[7:].strip() if header.startswith('Bearer ') else ''
            entity = world.authenticate(key)
            if entity is None:
                self._error(HTTPStatus.UNAUTHORIZED, 'unauthorized', 'valid Bearer arkw_ key required')
            return entity

        def do_GET(self):
            if not self._host_ok():
                return
            url = urlparse(self.path)
            if url.path in ('/', '/index.html'):
                return self._serve_client()
            if url.path == '/api/world':
                return self._send_json(HTTPStatus.OK, {'ok': True, **world.snapshot()})
            if url.path == '/api/me':
                entity = self._auth()
                if entity:
                    self._send_json(HTTPStatus.OK, {'ok': True, 'entity': entity})
                return
            if url.path == '/api/events':
                return self._stream(parse_qs(url.query))
            self._error(HTTPStatus.NOT_FOUND, 'not_found', 'no such route')

        def do_POST(self):
            if not self._host_ok():
                return
            if urlparse(self.path).path != '/api/actions':
                return self._error(HTTPStatus.NOT_FOUND, 'not_found', 'no such route')
            entity = self._auth()
            if entity is None:
                return
            length = int(self.headers.get('Content-Length') or 0)
            if not 0 < length <= MAX_BODY:
                return self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, 'bad_body',
                                   f'JSON body of 1-{MAX_BODY} bytes required')
            try:
                action = json.loads(self.rfile.read(length))
                if not isinstance(action, dict):
                    raise ValueError
            except ValueError:
                return self._error(HTTPStatus.BAD_REQUEST, 'bad_json', 'body must be a JSON object')
            if not limiter.allow(entity['id']):
                return self._error(HTTPStatus.TOO_MANY_REQUESTS, 'rate_limited',
                                   f'max {RATE_MAX_ACTIONS} actions per {int(RATE_WINDOW_S)}s')
            try:
                events = world.act(entity['id'], action)
            except Rejected as exc:
                return self._error(HTTPStatus.CONFLICT, exc.code, exc.message)
            self._send_json(HTTPStatus.OK, {'ok': True, 'events': events})

        def _serve_client(self):
            data = CLIENT_HTML.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Content-Security-Policy',
                             "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                             "script-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def _stream(self, query):
            try:
                seq = int(query.get('since', ['0'])[0])
            except ValueError:
                return self._error(HTTPStatus.BAD_REQUEST, 'bad_since', 'since must be an integer')
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.close_connection = True
            try:
                while not self.server.stopping:
                    batch = world.events_after(seq, SSE_WAIT_S)
                    if not batch:
                        self.wfile.write(b': keep-alive\n\n')
                    for event in batch:
                        payload = json.dumps(event, ensure_ascii=False)
                        self.wfile.write(f'id: {event["seq"]}\ndata: {payload}\n\n'.encode('utf-8'))
                        seq = event['seq']
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    return Handler


def serve(world: World, port: int) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((LOOPBACK, port), make_handler(world, port))
    httpd.daemon_threads = True
    httpd.stopping = False
    return httpd


def stop(httpd: ThreadingHTTPServer, world: World) -> None:
    httpd.stopping = True
    with world.cond:
        world.cond.notify_all()
    httpd.shutdown()
    httpd.server_close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='ARKAIOS WORLD reference server')
    sub = parser.add_subparsers(dest='cmd', required=True)
    for name in ('serve', 'register', 'revoke', 'list'):
        p = sub.add_parser(name)
        p.add_argument('--state', required=True, type=Path)
        p.add_argument('--world', type=Path, default=DEFAULT_DEFINITION)
        if name == 'serve':
            p.add_argument('--port', type=int, default=4300)
        if name == 'register':
            p.add_argument('--type', required=True, choices=['agent', 'human'])
            p.add_argument('--name', required=True)
            p.add_argument('--owner', required=True)
            p.add_argument('--alias', action='append', default=[])
            p.add_argument('--trust', default='sandboxed', choices=['sandboxed', 'trusted', 'core'])
            p.add_argument('--provider', default='')
            p.add_argument('--capability', action='append', default=[])
            p.add_argument('--memory-ref', default='')
        if name == 'revoke':
            p.add_argument('--id', required=True)
            p.add_argument('--reason', required=True)
    args = parser.parse_args(argv)

    world = World(args.state, args.world)
    try:
        if args.cmd == 'serve':
            httpd = serve(world, args.port)
            sys.stderr.write(f'ARKAIOS WORLD on http://{LOOPBACK}:{args.port} (seq {world.state.seq})\n')
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                stop(httpd, world)
        elif args.cmd == 'register':
            entity, key = world.register({
                'type': args.type, 'display_name': args.name, 'owner': args.owner,
                'aliases': args.alias, 'trust_level': args.trust, 'provider': args.provider,
                'capabilities': args.capability, 'memory_ref': args.memory_ref})
            json.dump({'entity': entity, 'key': key,
                       'note': 'Key shown once. Store it in an environment variable.'},
                      sys.stdout, ensure_ascii=False, indent=1)
            sys.stdout.write('\n')
        elif args.cmd == 'revoke':
            world.revoke(args.id, args.reason)
            sys.stdout.write(f'revoked {args.id}\n')
        elif args.cmd == 'list':
            json.dump(world.snapshot()['entities'], sys.stdout, ensure_ascii=False, indent=1)
            sys.stdout.write('\n')
    except Rejected as exc:
        sys.stderr.write(f'rejected: {exc.code}: {exc.message}\n')
        return 2
    finally:
        world.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
