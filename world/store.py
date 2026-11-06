"""Persistence for the reference world: append-only event log + hashed keys.

State directory layout (keep it private; it is git-ignored):
  events.jsonl  one event per line, fsync'd before the event is visible
  keys.json     {sha256(key): entity_id}; the key itself is never stored
  world.lock    held by the process that owns the state (one writer)
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import threading

from state import WorldState, load_world_definition

KEY_PREFIX = 'arkw_'


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


class StateLock:
    """Exclusive OS-level lock; released automatically if the process dies."""

    def __init__(self, path: Path):
        self.path = path
        self.handle = None

    def acquire(self) -> None:
        self.handle = open(self.path, 'a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.handle.close()
            self.handle = None
            raise RuntimeError(f'state directory is in use by another process ({self.path})')

    def release(self) -> None:
        if self.handle is None:
            return
        try:
            if os.name == 'nt':
                import msvcrt
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            self.handle.close()
            self.handle = None


class World:
    """Owns the state directory. All mutations go through `_commit` under one lock."""

    def __init__(self, state_dir: Path, definition_path: Path, registry_id: str = 'local-alpha'):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.lock = StateLock(self.state_dir / 'world.lock')
        self.lock.acquire()
        definition = load_world_definition(json.loads(Path(definition_path).read_text('utf-8')))
        self.state = WorldState(definition, registry_id)
        self.events = []
        self.cond = threading.Condition()
        self.log_path = self.state_dir / 'events.jsonl'
        self.keys_path = self.state_dir / 'keys.json'
        self.keys = self._load_keys()
        self._replay()

    def close(self) -> None:
        self.lock.release()

    def _load_keys(self) -> dict:
        if not self.keys_path.exists():
            return {}
        return json.loads(self.keys_path.read_text('utf-8'))

    def _save_keys(self) -> None:
        tmp = self.keys_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.keys, indent=1), 'utf-8')
        os.replace(tmp, self.keys_path)

    def _replay(self) -> None:
        if not self.log_path.exists():
            return
        with open(self.log_path, encoding='utf-8') as fh:
            for line_no, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    raise ValueError(f'events.jsonl line {line_no} is corrupt; refusing to start')
                self.state.apply(event)
                self.events.append(event)

    def _commit(self, drafts: list) -> list:
        """drafts: [(type, actor, target, payload)] -> persisted, applied events."""
        now = utc_now()
        out = []
        seq = self.state.seq
        for etype, actor, target, payload in drafts:
            seq += 1
            out.append({'v': 1, 'seq': seq, 'event_id': 'evt_' + secrets.token_hex(12),
                        'type': etype, 'timestamp': now, 'world': self.state.definition['id'],
                        'actor': actor, 'target': target, 'payload': payload})
        if not out:
            return out
        with open(self.log_path, 'a', encoding='utf-8') as fh:
            for event in out:
                fh.write(json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n')
            fh.flush()
            os.fsync(fh.fileno())
        for event in out:
            self.state.apply(event)
            self.events.append(event)
        self.cond.notify_all()
        return out

    # ----- public API (thread-safe) -----

    def register(self, spec: dict) -> tuple:
        with self.cond:
            drafts = self.state.decide_register(spec, utc_now())
            events = self._commit(drafts)
            entity_id = events[0]['target']
            key = KEY_PREFIX + secrets.token_hex(24)
            self.keys[hash_key(key)] = entity_id
            self._save_keys()
            return self.state.entities[entity_id], key

    def revoke(self, entity_id: str, reason: str) -> list:
        with self.cond:
            events = self._commit(self.state.decide_revoke(entity_id, reason))
            self.keys = {h: e for h, e in self.keys.items() if e != entity_id}
            self._save_keys()
            return events

    def authenticate(self, key: str):
        if not key or not key.startswith(KEY_PREFIX):
            return None
        with self.cond:
            entity_id = self.keys.get(hash_key(key))
            entity = self.state.entities.get(entity_id) if entity_id else None
            return entity if entity and entity['status'] == 'active' else None

    def act(self, actor_id: str, action: dict) -> list:
        with self.cond:
            return self._commit(self.state.decide_action(actor_id, action))

    def snapshot(self) -> dict:
        with self.cond:
            return self.state.snapshot()

    def events_after(self, seq: int, timeout: float) -> list:
        """Events with seq > `seq`; waits up to `timeout` seconds for new ones."""
        with self.cond:
            if self.state.seq <= seq:
                self.cond.wait(timeout)
            return self.events[max(seq, 0):]
