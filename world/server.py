"""ARKAIOS WORLD reference server v0.1 (loopback only, stdlib only).

  python world/server.py serve    --state DIR [--port 4300]
  python world/server.py register --state DIR --type agent --name Codex --alias codex \
                                  --owner "Operador ARKAIOS" --trust core [--capability coding]
  python world/server.py revoke   --state DIR --id ark:local-alpha:3 --reason "..."
  python world/server.py list     --state DIR

register/revoke/list need the server stopped (one writer per state dir).
The access key is printed once by `register`; only its SHA-256 is stored.
"""
import argparse
import hashlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
from pathlib import Path
import sys
import threading
import time
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mail import public_view  # noqa: E402
from state import Rejected  # noqa: E402
from store import World  # noqa: E402
from agents_autonomy import AgentsController  # noqa: E402
from chat_system import init_db as init_chat_db  # noqa: E402
from feedback_system import init_db as init_feedback_db  # noqa: E402
from visitor_sessions import VisitorSessions  # noqa: E402

HERE = Path(__file__).resolve().parent
DEFAULT_DEFINITION = HERE / 'world.json'
CLIENT_HTML = HERE / 'client' / 'index.html'
PAGES = {  # extra static files the client serves, with their content type
    '/simulacion': (HERE / 'client' / 'simulacion.html', 'text/html; charset=utf-8'),
    '/sim/apartment-map.js': (HERE / 'client' / 'apartment-map.js', 'application/javascript; charset=utf-8'),
    '/ecosystem': (HERE / 'client' / 'ecosystem-viewer.html', 'text/html; charset=utf-8'),
    '/map': (HERE / 'client' / 'world-map.html', 'text/html; charset=utf-8'),
    '/character-creator': (HERE / 'client' / 'character-creator.html', 'text/html; charset=utf-8'),
}
ASSETS_DIR = HERE / 'client' / 'assets'
ASSET_RE = re.compile(r'^/assets/([a-z_]{1,24})\.(png|webp|mp4)$')
LOOPBACK = '127.0.0.1'
MAX_BODY = 4096
RATE_WINDOW_S = 10.0
RATE_MAX_ACTIONS = 20
SSE_WAIT_S = 15.0
BOOT_ID = format(time.time_ns(), 'x')
agents_controller = None  # Global reference, set in main()


def client_version() -> str:
    """Changes when the page, any asset or the server process changes: open pages reload."""
    digest = hashlib.sha256(BOOT_ID.encode())
    for path in [CLIENT_HTML, *(page for page, _ in PAGES.values()), *sorted(ASSETS_DIR.glob('*.png'))]:
        st = path.stat()
        digest.update(f'{path.name}:{st.st_mtime_ns}:{st.st_size};'.encode())
    return digest.hexdigest()[:16]


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


def _allow_external() -> bool:
    return (os.environ.get('ALLOW_EXTERNAL', '').lower() in ('1', 'true', 'yes')
            or os.environ.get('ENVIRONMENT', '').lower() == 'production'
            or os.environ.get('ARKAIOS_ALLOW_TAILSCALE', '0') == '1')


def make_handler(world: World, port: int, agents_controller: AgentsController = None):
    allowed_hosts = {f'{LOOPBACK}:{port}', f'localhost:{port}', f'100.89.203.88:{port}', f'100.90.81.75:{port}'}
    allow_external = _allow_external()
    limiter = RateLimiter(RATE_WINDOW_S, RATE_MAX_ACTIONS)
    feedback_limiter = RateLimiter(60.0, 6)
    visitor_sessions = VisitorSessions()

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
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.end_headers()
            self.wfile.write(data)

        def _error(self, status: int, code: str, message: str) -> None:
            self._send_json(status, {'ok': False, 'error': code, 'message': message})

        def _host_ok(self) -> bool:
            if allow_external:
                return True
            # Blocks DNS-rebinding while permitting loopback and Tailscale CGNAT IP ranges (100.x.x.x)
            host_header = self.headers.get('Host', '')
            host_only = host_header.split(':')[0].strip().lower()
            if (host_header in allowed_hosts or
                host_only in ('127.0.0.1', 'localhost', '100.89.203.88', '100.90.81.75') or
                host_only.startswith('100.')):
                return True
            self._error(HTTPStatus.FORBIDDEN, 'bad_host', 'loopback or tailscale host required')
            return False

        def _auth(self):
            header = self.headers.get('Authorization', '')
            key = header[7:].strip() if header.startswith('Bearer ') else ''
            entity = world.authenticate(key)
            if entity is None:
                self._error(HTTPStatus.UNAUTHORIZED, 'unauthorized', 'valid Bearer arkw_ key required')
            return entity

        def _visitor_auth(self):
            session = visitor_sessions.verify(self.headers.get('X-Arkaios-Visitor-Session', ''))
            if session is None:
                self._error(HTTPStatus.UNAUTHORIZED, 'visitor_login_required',
                            'sign in with Google before publishing public feedback')
            return session

        def do_GET(self):
            if not self._host_ok():
                return
            url = urlparse(self.path)
            if url.path in ('/', '/index.html'):
                return self._serve_client()
            if url.path == '/login':
                return self._serve_client(HERE / 'client' / 'login.html', 'text/html; charset=utf-8')
            if url.path in PAGES:
                return self._serve_client(*PAGES[url.path])
            if ASSET_RE.match(url.path):
                m = ASSET_RE.match(url.path)
                return self._serve_asset(m.group(1), m.group(2))
            if url.path == '/api/version':
                return self._send_json(HTTPStatus.OK, {'ok': True, 'version': client_version()})
            if url.path == '/api/world':
                return self._send_json(HTTPStatus.OK, {'ok': True, **world.snapshot()})
            if url.path == '/api/debug/agents':
                if agents_controller:
                    return self._send_json(HTTPStatus.OK, agents_controller.get_debug_state())
                return self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {'ok': False, 'error': 'agents_not_ready'})
            if url.path == '/api/me':
                entity = self._auth()
                if entity:
                    self._send_json(HTTPStatus.OK, {'ok': True, 'entity': entity})
                return
            if url.path == '/api/simulation':
                entity = self._auth()
                if entity:
                    session = world.simulation(entity['id'], parse_qs(url.query).get('session', [''])[0])
                    if session is None:
                        return self._error(HTTPStatus.FORBIDDEN, 'not_player',
                                           'only the two players of that session can read its story')
                    self._send_json(HTTPStatus.OK, {'ok': True, 'session': session})
                return
            if url.path == '/api/inbox':
                entity = self._auth()
                if entity:
                    try:
                        since = int(parse_qs(url.query).get('since', ['0'])[0])
                    except ValueError:
                        return self._error(HTTPStatus.BAD_REQUEST, 'bad_since', 'since must be an integer')
                    self._send_json(HTTPStatus.OK, {'ok': True, **world.inbox(entity['id'], since)})
                return
            if url.path == '/api/events':
                return self._stream(parse_qs(url.query))
            if url.path == '/api/chat/history':
                return self._get_chat_history()
            if url.path == '/api/feedback':
                return self._get_public_feedback()
            if url.path == '/api/feedback/summary':
                return self._get_feedback_summary()
            self._error(HTTPStatus.NOT_FOUND, 'not_found', 'no such route')

        def _handle_google_auth(self):
            try:
                content_len = int(self.headers.get('Content-Length', 0))
                if not 0 < content_len <= MAX_BODY:
                    return self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, 'bad_body', 'credential required')
                body = self.rfile.read(content_len).decode('utf-8')
                data = json.loads(body)
                id_token = data.get('id_token', '')
                if (not isinstance(id_token, str) or len(id_token) > 8192 or
                        id_token.count('.') != 2):
                    return self._error(HTTPStatus.BAD_REQUEST, 'invalid_credential', 'Google credential required')
                client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
                if not client_id:
                    return self._error(HTTPStatus.SERVICE_UNAVAILABLE, 'login_unconfigured', 'Google login is not configured')
                try:
                    from google.auth.transport import requests as google_requests
                    from google.oauth2 import id_token as google_id_token
                    class TimedGoogleRequest(google_requests.Request):
                        def __call__(self, *args, **kwargs):
                            kwargs['timeout'] = min(float(kwargs.get('timeout', 5)), 5)
                            return super().__call__(*args, **kwargs)
                    claims = google_id_token.verify_oauth2_token(id_token, TimedGoogleRequest(), client_id)
                except ImportError:
                    return self._error(HTTPStatus.SERVICE_UNAVAILABLE, 'login_unavailable', 'Google verification dependency unavailable')
                except ValueError:
                    return self._error(HTTPStatus.UNAUTHORIZED, 'invalid_credential', 'Google credential could not be verified')
                if claims.get('iss') not in ('accounts.google.com', 'https://accounts.google.com') or not claims.get('sub'):
                    return self._error(HTTPStatus.UNAUTHORIZED, 'invalid_credential', 'unexpected Google identity')
                name = str(claims.get('name') or claims.get('given_name') or 'Visitante').strip()[:40] or 'Visitante'
                session = visitor_sessions.issue(claims['sub'], name)
                return self._send_json(HTTPStatus.OK, {
                    'ok': True,
                    'visitor_session': session,
                    'display_name': name,
                    'message': f'Bienvenido, {name}'
                })
            except Exception as e:
                sys.stderr.write(f'[ERROR] Google auth failed: {str(e)}\n')
                return self._error(HTTPStatus.INTERNAL_SERVER_ERROR, 'auth_error', str(e))

        def do_POST(self):
            if not self._host_ok():
                return
            path = urlparse(self.path).path
            if path == '/api/auth/google':
                return self._handle_google_auth()
            if path == '/api/chat/send':
                return self._handle_chat_message()
            if path == '/api/feedback':
                return self._handle_public_feedback()
            if path != '/api/actions':
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

        def _handle_chat_message(self):
            entity = self._auth()
            if entity is None:
                return
            length = int(self.headers.get('Content-Length') or 0)
            if not 0 < length <= MAX_BODY:
                return self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, 'bad_body', 'body too large')
            try:
                data = json.loads(self.rfile.read(length))
                msg = data.get('message', '').strip()
                chat_type = data.get('type', 'chat')
                if not msg:
                    return self._error(HTTPStatus.BAD_REQUEST, 'empty_message', 'message required')
                from chat_system import ChatMessage, save_message
                chat_msg = ChatMessage(entity['id'], entity.get('display_name', 'Unknown'), msg, chat_type)
                save_message(chat_msg)
                self._send_json(HTTPStatus.OK, {'ok': True, 'msg_id': chat_msg.id})
            except Exception as e:
                return self._error(HTTPStatus.BAD_REQUEST, 'chat_error', str(e))

        def _handle_public_feedback(self):
            length = int(self.headers.get('Content-Length') or 0)
            if not 0 < length <= MAX_BODY:
                return self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, 'bad_body', 'body too large')
            try:
                # Always consume the request body before returning an error.  The
                # HTTP/1.1 connection can otherwise misparse it as a new request.
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('invalid_payload')
                # Keep the public feedback surface local by default.  A deployment
                # must consciously opt in instead of becoming a spam endpoint.
                if allow_external and os.environ.get('ARKAIOS_PUBLIC_FEEDBACK', '0') != '1':
                    return self._error(HTTPStatus.FORBIDDEN, 'feedback_disabled',
                                       'public feedback is not enabled for this deployment')
                if not feedback_limiter.allow(self.client_address[0]):
                    return self._error(HTTPStatus.TOO_MANY_REQUESTS, 'rate_limited',
                                       'try again in a minute')
                visitor = self._visitor_auth()
                if visitor is None:
                    return
                from feedback_system import create_feedback
                record = create_feedback(visitor['name'], data.get('category'), data.get('message'))
                self._send_json(HTTPStatus.CREATED, {'ok': True, 'feedback': record})
            except (ValueError, json.JSONDecodeError):
                return self._error(HTTPStatus.BAD_REQUEST, 'invalid_feedback',
                                   'a visible name, category, and short message are required')

        def _get_public_feedback(self):
            try:
                from feedback_system import get_public_feedback
                self._send_json(HTTPStatus.OK, {'ok': True, 'feedback': get_public_feedback()})
            except Exception as exc:
                return self._error(HTTPStatus.INTERNAL_SERVER_ERROR, 'feedback_error', str(exc))

        def _get_feedback_summary(self):
            entity = self._auth()
            if entity is None:
                return
            if entity.get('type') != 'agent':
                return self._error(HTTPStatus.FORBIDDEN, 'agent_only',
                                   'only registered agents can request the feedback summary')
            from feedback_system import feedback_summary
            self._send_json(HTTPStatus.OK, {'ok': True, 'summary': feedback_summary()})

        def _serve_client(self, path=CLIENT_HTML, content_type='text/html; charset=utf-8'):
            data = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-cache')
            if path.name == 'login.html':
                csp = ("default-src 'self'; "
                       "style-src 'self' 'unsafe-inline' https://accounts.google.com; "
                       "script-src 'self' 'unsafe-inline' https://accounts.google.com; "
                       "frame-src https://accounts.google.com; "
                       "connect-src 'self' https://accounts.google.com; "
                       "frame-ancestors 'none'")
            else:
                csp = ("default-src 'self'; media-src 'self'; style-src 'self' 'unsafe-inline'; "
                       "script-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
            self.send_header('Content-Security-Policy', csp)
            self.end_headers()
            self.wfile.write(data)

        def _serve_asset(self, name, ext='png'):
            path = ASSETS_DIR / f'{name}.{ext}'
            if not path.is_file():
                return self._error(HTTPStatus.NOT_FOUND, 'not_found', 'no such asset')
            st = path.stat()
            etag = f'"{st.st_mtime_ns:x}-{st.st_size:x}"'
            if self.headers.get('If-None-Match') == etag:
                self.send_response(HTTPStatus.NOT_MODIFIED)
                self.send_header('ETag', etag)
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                return
            data = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            mime = {'webp': 'image/webp', 'mp4': 'video/mp4'}.get(ext, 'image/png')
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('ETag', etag)
            self.send_header('X-Content-Type-Options', 'nosniff')
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
                        payload = json.dumps(public_view(event), ensure_ascii=False)
                        self.wfile.write(f'id: {event["seq"]}\ndata: {payload}\n\n'.encode('utf-8'))
                        seq = event['seq']
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def _get_chat_history(self):
            try:
                from chat_system import get_recent_messages
                messages = get_recent_messages(limit=50)
                self._send_json(HTTPStatus.OK, {'ok': True, 'messages': messages})
            except Exception as e:
                return self._error(HTTPStatus.INTERNAL_SERVER_ERROR, 'chat_error', str(e))

    return Handler


def serve(world: World, port: int, host: str = None, agents_controller: AgentsController = None) -> ThreadingHTTPServer:
    bind_host = host if host is not None else ('0.0.0.0' if _allow_external() else LOOPBACK)
    httpd = ThreadingHTTPServer((bind_host, port), make_handler(world, port, agents_controller))
    httpd.daemon_threads = True
    httpd.stopping = False
    return httpd


def stop(httpd: ThreadingHTTPServer, world: World) -> None:
    httpd.stopping = True
    with world.cond:
        world.cond.notify_all()
    httpd.shutdown()
    httpd.server_close()


def ensure_base_citizens(world: World) -> None:
    """Ensure base 4 citizens exist (for Render cold-start)."""
    snapshot = world.snapshot()
    entities = snapshot.get('entities', {})

    base_citizens = {
        'Arkaios': {'type': 'human', 'owner': 'Arkaios', 'trust': 'core'},
        'Codex': {'type': 'agent', 'owner': 'Arkaios', 'trust': 'core', 'caps': ['coding', 'orchestration']},
        'ELEMIA': {'type': 'agent', 'owner': 'Arkaios', 'trust': 'core', 'caps': ['graphics']},
        'NINA': {'type': 'agent', 'owner': 'Arkaios', 'trust': 'core', 'caps': ['monitoring']},
        'Chai-Gati-Pet': {'type': 'agent', 'owner': 'Arkaios', 'trust': 'trusted',
                          'caps': ['orchestration', 'governance', 'custody', 'memory']},
    }

    for name, cfg in base_citizens.items():
        # Check if citizen exists
        entity_list = list(entities.values()) if isinstance(entities, dict) else (entities if isinstance(entities, list) else [])
        exists = any(e.get('display_name') == name for e in entity_list)
        if not exists:
            try:
                entity, key = world.register({
                    'type': cfg['type'],
                    'display_name': name,
                    'owner': cfg['owner'],
                    'aliases': [name.lower()],
                    'trust_level': cfg['trust'],
                    'capabilities': cfg.get('caps', [])
                })
                sys.stderr.write(f'[BOOT] Registered {name}: {entity["id"]}\n')
            except Exception as e:
                sys.stderr.write(f'[BOOT] Failed to register {name}: {e}\n')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='ARKAIOS WORLD reference server')
    sub = parser.add_subparsers(dest='cmd', required=True)
    for name in ('serve', 'register', 'revoke', 'list'):
        p = sub.add_parser(name)
        p.add_argument('--state', required=True, type=Path)
        p.add_argument('--world', type=Path, default=DEFAULT_DEFINITION)
        if name == 'serve':
            default_port = int(os.environ.get('PORT') or os.environ.get('WORLD_PORT') or 4300)
            p.add_argument('--port', type=int, default=default_port)
            p.add_argument('--host', default=None)
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
            ensure_base_citizens(world)
            init_chat_db()
            init_feedback_db()
            bind_host = args.host if args.host is not None else ('0.0.0.0' if _allow_external() else LOOPBACK)

            # Create and start agents controller
            global agents_controller
            agents_controller = AgentsController(
                world_state_getter=lambda: world.snapshot(),
                action_executor=lambda eid, act: world.act(eid, act)
            )
            agents_controller.start()

            httpd = serve(world, args.port, bind_host, agents_controller)
            sys.stderr.write(f'ARKAIOS WORLD on http://{bind_host}:{args.port} (seq {world.state.seq})\n')
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                agents_controller.stop()
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
