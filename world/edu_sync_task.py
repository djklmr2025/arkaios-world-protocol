"""Scheduled-task entry point (run with pythonw.exe, no window).

  1. Watchdog: if the world does not answer on 127.0.0.1:4300, start it detached
     (a second server exits on the state-dir lock, so repeating this is safe).
  2. Brings new Educación Libre template requests onto the task board.

Everything goes to .local-world/edu-sync.log; it never raises.
"""
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import time
import traceback
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
REPO = Path(__file__).resolve().parent.parent
STATE = REPO / '.local-world'
LOG = STATE / 'edu-sync.log'
WORLD_VERSION_URL = 'http://127.0.0.1:4300/api/version'
START_WAIT_S = 15
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
CREATE_NO_WINDOW = 0x08000000


def log(text: str) -> None:
    with LOG.open('a', encoding='utf-8') as f:
        f.write(f'[{datetime.now():%Y-%m-%d %H:%M:%S}] {text}\n')


def world_up() -> bool:
    try:
        with urllib.request.urlopen(WORLD_VERSION_URL, timeout=3) as resp:
            return resp.status == 200
    except OSError:
        return False


def start_world() -> None:
    python = Path(sys.executable).with_name('python.exe')
    server_log = (STATE / 'server.log').open('ab')
    args = [str(python), 'world/server.py', 'serve', '--state', '.local-world', '--port', '4300']
    flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
    try:
        subprocess.Popen(args, cwd=REPO, stdout=server_log, stderr=server_log,
                         stdin=subprocess.DEVNULL, creationflags=flags | CREATE_BREAKAWAY_FROM_JOB)
    except OSError:  # the task's job may forbid breakaway
        subprocess.Popen(args, cwd=REPO, stdout=server_log, stderr=server_log,
                         stdin=subprocess.DEVNULL, creationflags=flags)


def ensure_world() -> bool:
    if world_up():
        return True
    log('ARKAIOS World no respondía en :4300; arrancándolo.')
    start_world()
    for _ in range(START_WAIT_S):
        time.sleep(1)
        if world_up():
            log('ARKAIOS World arriba.')
            return True
    log('ARKAIOS World sigue sin responder; revisa .local-world/server.log')
    return False


def sync_requests() -> None:
    from edu_inbox_bridge import fetch_requests, load_ledger, read_env, save_ledger, sync
    from presence_hook import Client, read_key
    key, edu_key = read_key('claude'), read_env('ARKAIOS_EDU_AGENT_KEY')
    if not key or not edu_key:
        log('Faltan ARKAIOS_WORLD_KEY_CLAUDE o ARKAIOS_EDU_AGENT_KEY.')
        return
    items = fetch_requests(edu_key=edu_key)
    result = sync(items, Client(key), load_ledger())
    save_ledger(result['ledger'])
    for edu_id, task_id, title in result['posted']:
        log(f'{edu_id} -> {task_id}  {title}')
    log(f"origen: {len(items)} | nuevas: {len(result['posted'])} | descartadas: {result['skipped']}"
        + (f" | detenido: {result['error']}" if result['error'] else ''))


def main() -> int:
    try:
        if ensure_world():
            sync_requests()
    except Exception:  # noqa: BLE001 - a background task must log, not crash silently
        log('Error: ' + traceback.format_exc().strip().replace('\n', ' | '))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
