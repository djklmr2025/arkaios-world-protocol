"""Wake an agent's avatar when its session starts and put it to sleep when it ends.

  python world/presence_hook.py --agent claude start   # join, go home, sit, show inbox
  python world/presence_hook.py --agent claude end     # sleep when the last session ends

Works as a Claude Code SessionStart/SessionEnd hook (reads the hook JSON on stdin for
`session_id`; on start, stdout becomes session context) or by hand for any agent.
The key comes from ARKAIOS_WORLD_KEY_<AGENT> (process env, else the Windows user env).
Never raises: if the world is down the session just starts normally.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

WORLD = os.environ.get('ARKAIOS_WORLD_URL', 'http://127.0.0.1:4300')
TIMEOUT_S = 3
SESSION_TTL_S = 12 * 3600
SEAT_ORDER = ('chair', 'sofa', 'beanbag')


def read_key(agent: str) -> str:
    name = f'ARKAIOS_WORLD_KEY_{agent.upper()}'
    key = os.environ.get(name, '')
    if not key and os.name == 'nt':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as reg:
                key = winreg.QueryValueEx(reg, name)[0]
        except OSError:
            key = ''
    return key


class Client:
    def __init__(self, key: str):
        self.key = key

    def call(self, method: str, path: str, body=None):
        data = json.dumps(body).encode('utf-8') if body is not None else None
        req = urllib.request.Request(WORLD + path, data=data, method=method, headers={
            'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as err:
            return json.loads(err.read() or b'{}')

    def act(self, **action):
        return self.call('POST', '/api/actions', action)


def sessions_file(agent: str) -> Path:
    base = Path(os.environ.get('LOCALAPPDATA') or Path.home() / '.local' / 'state')
    path = base / 'arkaios-world' / f'{agent}-sessions.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def update_sessions(agent: str, session_id: str, active: bool) -> int:
    path = sessions_file(agent)
    try:
        sessions = json.loads(path.read_text('utf-8'))
    except (OSError, ValueError):
        sessions = {}
    now = time.time()
    sessions = {k: v for k, v in sessions.items() if now - v < SESSION_TTL_S and k != session_id}
    if active:
        sessions[session_id] = now
    path.write_text(json.dumps(sessions), 'utf-8')
    return len(sessions)


def find_seat(home: dict):
    seats = [i for i in home.get('items', []) if i['layer'] == 'object' and i['item'] in SEAT_ORDER]
    seats.sort(key=lambda i: SEAT_ORDER.index(i['item']))
    return seats[0] if seats else None


def wake(client: Client, me: dict, world: dict) -> str:
    my_id = me['id']
    home_id = f"room:casas:{my_id.rsplit(':', 1)[1]}"
    home = next((h for h in world.get('homes', []) if h['id'] == home_id), None)
    presence = world.get('presence', {}).get(my_id)
    if presence is None:
        client.act(type='join', room=home_id if home else world['world']['spawn'])
    elif home and presence['room'] != home_id:
        client.act(type='move', room=home_id)
    seat = find_seat(home) if home else None
    if seat:
        client.act(type='walk', x=seat['x'], y=seat['y'])
    client.act(type='status', status='busy', mood='working', note='en sesión')
    client.act(type='emote', emote='wave')
    inbox = client.call('GET', '/api/inbox')
    lines = [f"ARKAIOS World: {me['display_name']} despertó"
             f"{' en ' + home['name'] if home else ''} ({WORLD})."]
    unread = inbox.get('unread', 0)
    pending = [m for m in inbox.get('messages', []) + inbox.get('notices', [])
               if m['seq'] > inbox.get('read_upto', 0)]
    pending.sort(key=lambda m: m['seq'])
    names = {e['id']: e['display_name'] for e in world.get('entities', [])}
    lines.append(f'Buzón: {unread} sin leer.')
    for m in pending[-5:]:
        if 'text' in m:
            lines.append(f"- DM de {names.get(m['from'], m['from'])}: {m['text'][:200]}")
        else:
            lines.append(f"- Aviso {m['type']} de {names.get(m['actor'], m['actor'])}: {m.get('title', '')}")
    if unread:
        lines.append('Para marcar leído: POST /api/actions {"type":"dm_read","upto":<seq>} con tu llave.')
    return '\n'.join(lines)


def sleep(client: Client, me: dict, world: dict) -> None:
    my_id = me['id']
    if my_id not in world.get('presence', {}):
        return
    home_id = f"room:casas:{my_id.rsplit(':', 1)[1]}"
    home = next((h for h in world.get('homes', []) if h['id'] == home_id), None)
    if home and world['presence'][my_id]['room'] != home_id:
        client.act(type='move', room=home_id)
    bed = next((i for i in (home or {}).get('items', [])
                if i['layer'] == 'object' and i['item'] in ('sofa', 'beanbag')), None)
    if bed:
        client.act(type='walk', x=bed['x'], y=bed['y'])
    client.act(type='status', status='away', mood='sleeping', note='fuera de sesión')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--agent', required=True)
    parser.add_argument('event', choices=['start', 'end'])
    args = parser.parse_args(argv)
    session_id = 'manual'
    if not sys.stdin.isatty():
        try:
            session_id = str(json.loads(sys.stdin.read() or '{}').get('session_id') or 'manual')
        except ValueError:
            pass
    key = read_key(args.agent)
    if not key:
        return 0
    client = Client(key)
    try:
        me = client.call('GET', '/api/me').get('entity')
        if not me:
            return 0
        remaining = update_sessions(args.agent, session_id, args.event == 'start')
        world = client.call('GET', '/api/world')
        if args.event == 'start':
            sys.stdout.write(wake(client, me, world) + '\n')
        elif remaining == 0:
            sleep(client, me, world)
    except (OSError, ValueError, KeyError):
        return 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
