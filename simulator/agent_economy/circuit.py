"""Local service circuit. Real WAV rendering; synthetic payments; no remote APIs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import wave

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from economy import Economy

MUSIC_COMMIT = '2803142d68ff21baa595f63b254eeeb89c4c1e20'
SOURCE_HASHES = {
    'engine/spatial_model.py': 'c7a951d9fec4fce5df3c90b080d6590de239de86e0dd690a3e82d072cfd794ed',
    'engine/spatial_renderer.py': '3107f914955ac3f47585671c001af9ebe830c449744273e37deb302a10292838',
    'projects/test2_fondo_al_frente.json': 'ecb1905eae4ed5afbf81446e2a95ee9f07f02a2e8376e806be5a1db2b46e9761',
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value):
        raise ValueError('invalid local identifier')
    return value


def load_or_create_key(root, name):
    """Development-only local custody. Windows requires a private folder ACL."""
    folder = Path(root) / 'keys'
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = folder / (safe_id(name) + '.key')
    try:
        # Exclusive creation: never overwrite an existing identity.
        key = Ed25519PrivateKey.generate()
        raw = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                serialization.NoEncryption())
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as out:
            out.write(raw)
    except FileExistsError:
        pass
    return Ed25519PrivateKey.from_private_bytes(path.read_bytes())


class Circuit:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.ledger = Economy(str(self.root / 'state.sqlite'))
        self.db = self.ledger.db
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS identities(id TEXT PRIMARY KEY, public_key TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, buyer TEXT NOT NULL REFERENCES identities(id),
          seller TEXT NOT NULL REFERENCES identities(id), amount INTEGER NOT NULL,
          state TEXT NOT NULL, manifest TEXT);
        CREATE TABLE IF NOT EXISTS memories(agent TEXT NOT NULL REFERENCES identities(id),
          seq INTEGER NOT NULL, payload TEXT NOT NULL, previous_hash TEXT NOT NULL,
          hash TEXT NOT NULL, signature TEXT NOT NULL, PRIMARY KEY(agent,seq));
        ''')

    def register(self, name, key):
        safe_id(name)
        public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        old = self.db.execute('SELECT public_key FROM identities WHERE id=?', (name,)).fetchone()
        if old and old[0] != public:
            raise ValueError('identity key mismatch; rotation requires a separate protocol')
        def action():
            self.db.execute('INSERT OR IGNORE INTO identities VALUES (?,?)', (name, public))
            self.db.execute('INSERT OR IGNORE INTO accounts(id) VALUES (?)', (name,))
        self.ledger.transaction(action)

    def verify(self, identity, payload, signature):
        row = self.db.execute('SELECT public_key FROM identities WHERE id=?', (identity,)).fetchone()
        if not row:
            raise ValueError('unknown identity')
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(row[0])).verify(bytes.fromhex(signature), canonical(payload))

    def remember(self, identity, payload, key):
        # Assert signing key matches registration before appending.
        def action():
            row = self.db.execute('SELECT seq,hash FROM memories WHERE agent=? ORDER BY seq DESC LIMIT 1', (identity,)).fetchone()
            seq, previous = (row[0] + 1, row[1]) if row else (1, '0' * 64)
            envelope = {'domain': 'ark.local.memory.v1', 'agent': identity, 'seq': seq,
                        'previous': previous, 'payload': payload}
            raw = canonical(envelope)
            signature = key.sign(raw).hex()
            self.verify(identity, envelope, signature)
            self.db.execute('INSERT INTO memories VALUES (?,?,?,?,?,?)',
                            (identity, seq, raw.decode(), previous, hashlib.sha256(raw).hexdigest(), signature))
        self.ledger.transaction(action)

    def recall(self, identity):
        previous = '0' * 64
        result = []
        for expected, row in enumerate(self.db.execute(
                'SELECT seq,payload,previous_hash,hash,signature FROM memories WHERE agent=? ORDER BY seq', (identity,)), 1):
            seq, raw, prev, hashed, signature = row
            envelope = json.loads(raw)
            if seq != expected or prev != previous or hashlib.sha256(raw.encode()).hexdigest() != hashed:
                raise ValueError('memory chain mismatch')
            if envelope.get('agent') != identity or envelope.get('seq') != seq or envelope.get('previous') != prev:
                raise ValueError('memory envelope mismatch')
            self.verify(identity, envelope, signature)
            result.append(envelope['payload'])
            previous = hashed
        return result

    def request(self, task_id, buyer, seller, amount):
        safe_id(task_id)
        self.ledger.amount(amount)
        def action():
            old = self.db.execute('SELECT buyer,seller,amount FROM tasks WHERE id=?', (task_id,)).fetchone()
            if old and old != (buyer, seller, amount):
                raise ValueError('task payload mismatch')
            self.db.execute('INSERT OR IGNORE INTO tasks VALUES (?,?,?,?,?,NULL)',
                            (task_id, buyer, seller, amount, 'REQUESTED'))
        self.ledger.transaction(action)
        # Idempotent reservation can be retried if a crash occurs after task insert.
        self.ledger.reserve(task_id, buyer, seller, amount)
        self.db.execute("UPDATE tasks SET state='RESERVED' WHERE id=? AND state='REQUESTED'", (task_id,))

    def task(self, task_id):
        row = self.db.execute('SELECT buyer,seller,amount,state,manifest FROM tasks WHERE id=?', (task_id,)).fetchone()
        if not row:
            raise ValueError('unknown task')
        return dict(zip(('buyer','seller','amount','state','manifest'), row))

    def render(self, task_id, music_root, seller_key):
        task_id = safe_id(task_id)
        task = self.task(task_id)
        self.recall(task['seller'])  # Recover and verify context before doing work.
        if task['state'] in ('VERIFIED', 'ACCEPTED'):
            return self.verify_artifact(task_id)
        if task['state'] != 'RESERVED':
            raise ValueError('task is not reserved')
        source = Path(music_root).resolve()
        for relative, expected in SOURCE_HASHES.items():
            candidate = source / relative
            if candidate.is_symlink() or digest(candidate) != expected:
                raise ValueError('music source mismatch: ' + relative)
        output_dir = self.root / 'artifacts' / task_id
        output_dir.mkdir(parents=True, exist_ok=True)
        project_path = output_dir / 'project.json'
        project_path.write_bytes((source / 'projects/test2_fondo_al_frente.json').read_bytes())
        wav_path = output_dir / 'delivery.wav'
        # Fixed trusted worker; no shell, arbitrary commands, model or network.
        worker = Path(__file__).with_name('render_worker.py')
        subprocess.run([sys.executable, '-I', str(worker), str(source), str(project_path), str(wav_path)],
                       check=True, timeout=60, capture_output=True)
        report = inspect_wav(wav_path)
        payload = {'domain': 'ark.local.delivery.v1', 'task': task_id, 'seller': task['seller'],
                   'project_hash': digest(project_path), 'audio_hash': digest(wav_path),
                   'music_commit': MUSIC_COMMIT, 'audio': report}
        signed = {'payload': payload, 'signature': seller_key.sign(canonical(payload)).hex()}
        self.verify(task['seller'], payload, signed['signature'])
        manifest = json.dumps(signed, sort_keys=True)
        # Files are already complete. The DB transition is the delivery commit point.
        self.db.execute("UPDATE tasks SET state='VERIFIED',manifest=? WHERE id=? AND state='RESERVED'", (manifest, task_id))
        (output_dir / 'manifest.json').write_text(manifest, encoding='utf-8')
        self.remember(task['seller'], {'task': task_id, 'state': 'VERIFIED', 'audio_hash': payload['audio_hash']}, seller_key)
        return self.verify_artifact(task_id)

    def verify_artifact(self, task_id):
        safe_id(task_id)
        task = self.task(task_id)
        if not task['manifest']:
            raise ValueError('no delivery')
        signed = json.loads(task['manifest'])
        payload = signed['payload']
        self.verify(task['seller'], payload, signed['signature'])
        folder = self.root / 'artifacts' / task_id
        if payload['task'] != task_id or payload['seller'] != task['seller']:
            raise ValueError('delivery identity mismatch')
        if digest(folder / 'delivery.wav') != payload['audio_hash'] or digest(folder / 'project.json') != payload['project_hash']:
            raise ValueError('artifact modified')
        if inspect_wav(folder / 'delivery.wav') != payload['audio']:
            raise ValueError('audio metadata mismatch')
        return payload

    def acceptance_payload(self, task_id):
        task = self.task(task_id)
        artifact = self.verify_artifact(task_id)
        return {'domain': 'ark.local.accept.v1', 'task': task_id, 'buyer': task['buyer'],
                'seller': task['seller'], 'amount': task['amount'], 'audio_hash': artifact['audio_hash']}

    def accept(self, task_id, signature):
        payload = self.acceptance_payload(task_id)
        self.verify(payload['buyer'], payload, signature)
        self.ledger.finish(task_id, payload['buyer'], True)
        # Safe to retry after crash: finish is idempotent for this exact order.
        self.record_acceptance(task_id)
        return self.ledger.audit()

    def record_acceptance(self, task_id):
        self.db.execute("UPDATE tasks SET state='ACCEPTED' WHERE id=?", (task_id,))


def inspect_wav(path):
    import array
    with wave.open(str(path), 'rb') as audio:
        channels, width, rate, frames = audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getnframes()
        if channels != 2 or width != 2 or rate != 44100 or not 0 < frames <= 44100 * 10:
            raise ValueError('unexpected WAV format or duration')
        raw = audio.readframes(frames)
    if len(raw) != frames * channels * width:
        raise ValueError('truncated WAV')
    samples = array.array('h', raw)
    if sys.byteorder != 'little':
        samples.byteswap()
    peak = max(abs(x) for x in samples)
    if not 0 < peak < 32767:
        raise ValueError('silent or clipped audio')
    return {'channels': channels, 'sample_width': width, 'sample_rate': rate, 'frames': frames, 'peak_pcm': peak}


def demo(root, music_root):
    circuit = Circuit(root)
    buyer_key, seller_key = (load_or_create_key(root, name) for name in ('buyer', 'music-agent'))
    circuit.register('buyer', buyer_key)
    circuit.register('music-agent', seller_key)
    previous_context = circuit.recall('music-agent')
    if not previous_context:
        circuit.remember('music-agent', {'role': 'spatial-renderer', 'source': 'arkaios-music-studio',
                                       'objective': 'render supplied fixture, not compose a new song'}, seller_key)
    circuit.ledger.fund_test('demo-only-1000', 'buyer', 1000)
    circuit.request('render-001', 'buyer', 'music-agent', 250)
    delivery = circuit.render('render-001', music_root, seller_key)
    # This demo simulates explicit buyer acceptance; production must use an independent client.
    signature = buyer_key.sign(canonical(circuit.acceptance_payload('render-001'))).hex()
    audit = circuit.accept('render-001', signature)
    result = {'mode': 'LOCAL_SYNTHETIC_PAYMENT', 'task': circuit.task('render-001')['state'],
              'recovered_memories': len(previous_context), 'delivery': delivery,
              'buyer_balance': circuit.ledger.balance('buyer'), 'agent_balance': circuit.ledger.balance('music-agent'),
              'audit': audit}
    (Path(root) / 'report.json').write_bytes(canonical(result))
    circuit.db.close()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', required=True)
    parser.add_argument('--music-root', required=True)
    args = parser.parse_args()
    print(json.dumps(demo(args.state, args.music_root), indent=2))
