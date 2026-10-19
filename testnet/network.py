"""Four loopback validator processes for a bounded local test-network demonstration."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import multiprocessing as mp
import os
from pathlib import Path
import urllib.request

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ledger import Node, MAX_BLOCK_BYTES, canonical, genesis, hashed, public, registration, sign_tx, agent_id


def key_at(root, name):
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = root / (name + '.key')
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        key = Ed25519PrivateKey.generate()
        with os.fdopen(fd, 'wb') as f:
            f.write(key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                      serialization.NoEncryption()))
    except FileExistsError:
        pass
    return Ed25519PrivateKey.from_private_bytes(path.read_bytes())


def serve(db_path, config, validator_id, raw_key, port_queue):
    node = Node(db_path, config, validator_id, Ed25519PrivateKey.from_private_bytes(raw_key))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, value):
            raw = canonical(value)
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path != '/status':
                self.reply(404, {'ok': False})
                return
            try:
                state, height, tip = node.state()
                self.reply(200, {'ok': True, 'next_height': height, 'tip': tip, 'state_hash': hashed(state)})
            except Exception:
                self.reply(409, {'ok': False, 'error': 'CHAIN_INVALID'})

        def do_POST(self):
            self.connection.settimeout(5)
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_BLOCK_BYTES:
                    self.reply(413, {'ok': False, 'error': 'BODY_SIZE'})
                    return
                if self.path not in ('/vote', '/commit'):
                    self.reply(404, {'ok': False})
                    return
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError('truncated body')
                value = json.loads(raw)
                if self.path == '/vote':
                    result = {'ok': True, 'validator': validator_id, 'signature': node.vote(value)}
                else:
                    result = {'ok': True, 'block_hash': node.commit(value)}
                self.reply(200, result)
            except Exception:
                self.reply(400, {'ok': False, 'error': 'INVALID_PROPOSAL_OR_BLOCK'})

    server = HTTPServer(('127.0.0.1', 0), Handler)
    port_queue.put(server.server_address[1])
    try:
        server.serve_forever()
    finally:
        server.server_close()
        node.db.close()


def call(port, endpoint, value=None):
    # The test client never sends data to a non-loopback host or through proxies.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request('http://127.0.0.1:' + str(int(port)) + endpoint,
                                 data=None if value is None else canonical(value),
                                 headers={'Content-Type': 'application/json'})
    with opener.open(req, timeout=10) as response:
        result = json.loads(response.read(MAX_BLOCK_BYTES + 1))
    if result.get('ok') is not True:
        raise ValueError('node did not confirm')
    return result


class LoopbackNetwork:
    def __init__(self, root, config, keys):
        self.root, self.config, self.keys = Path(root), config, keys
        self.processes, self.ports = {}, {}

    def __enter__(self):
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            for identity, key in self.keys.items():
                queue = mp.Queue()
                raw = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                         serialization.NoEncryption())
                process = mp.Process(target=serve, args=(str(self.root / (identity + '.sqlite')),
                                     self.config, identity, raw, queue))
                process.start()
                self.processes[identity] = process
                try:
                    self.ports[identity] = queue.get(timeout=15)
                finally:
                    queue.close()
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        for process in self.processes.values():
            process.terminate()
        for process in self.processes.values():
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)

    def finalize(self, body, voters=None, recipients=None):
        voters = list(self.ports) if voters is None else voters
        recipients = list(self.ports) if recipients is None else recipients
        signatures = {}
        for identity in voters:
            result = call(self.ports[identity], '/vote', body)
            if result['validator'] != identity:
                raise ValueError('unexpected validator')
            signatures[identity] = result['signature']
        envelope = {'body': body, 'signatures': signatures}
        # Verify every collected vote before any commit, even when fewer than quorum.
        verifier = Node(self.root / 'coordinator.sqlite', self.config, next(iter(self.keys)), next(iter(self.keys.values())))
        try:
            verifier.certificate(body, signatures)
        finally:
            verifier.db.close()
        receipts = [call(self.ports[identity], '/commit', envelope) for identity in recipients]
        return envelope, receipts


def demo(root, artifact=None):
    root = Path(root).resolve()
    keys = {name: key_at(root / 'keys', name) for name in ('v1', 'v2', 'v3', 'v4')}
    registrar, buyer, provider, child = [key_at(root / 'keys', name) for name in ('registrar', 'buyer', 'provider', 'child')]
    config = genesis('arkaios-local-test', public(registrar), {name: public(key) for name, key in keys.items()})
    coordinator = Node(root / 'v1.sqlite', config, 'v1', keys['v1'])
    try:
        state, height, _ = coordinator.state()
        with LoopbackNetwork(root, config, keys) as network:
            if height == 1:
                stages = [
                    [registration(config, registrar, 'registrar', 1, buyer),
                     registration(config, registrar, 'registrar', 2, provider)],
                    [registration(config, provider, agent_id(config, 2), 1, child),
                     sign_tx(config, registrar, 'registrar', 3, 'test.fund', {'recipient': agent_id(config, 1), 'amount': 1000}),
                     sign_tx(config, buyer, agent_id(config, 1), 1, 'bridge.lock_mint', {'amount': 600})],
                    [sign_tx(config, buyer, agent_id(config, 1), 2, 'token.transfer', {'recipient': agent_id(config, 2), 'amount': 250}),
                     sign_tx(config, provider, agent_id(config, 2), 2, 'bridge.burn_redeem', {'amount': 250})],
                ]
                for transactions in stages:
                    network.finalize(coordinator.propose(transactions))
            elif height not in (4,5):
                raise ValueError('partial demo state; inspect and recover explicitly')
            if artifact is not None:
                artifact_hash = hashlib.sha256(Path(artifact).read_bytes()).hexdigest()
                current, next_height, _ = coordinator.state()
                reference = agent_id(config, 2) + ':render-001'
                if reference in current['artifacts']:
                    if current['artifacts'][reference]['sha256'] != artifact_hash:
                        raise ValueError('anchored artifact differs')
                else:
                    tx = sign_tx(config, provider, agent_id(config, 2), current['nonces'][agent_id(config, 2)]+1,
                                 'artifact.anchor', {'sha256': artifact_hash, 'task_ref': 'render-001'})
                    network.finalize(coordinator.propose([tx]))
            status = [call(port, '/status') for port in network.ports.values()]
            if len({s['state_hash'] for s in status}) != 1:
                raise ValueError('replicas diverged')
        state, height, tip = coordinator.state()
        result = {'mode': 'TEST_ONLY', 'validators': 4, 'quorum': 3, 'blocks': height - 1,
                  'max_block_bytes': MAX_BLOCK_BYTES, 'state_hash': hashed(state), 'tip': tip,
                  'issued_amr_test': state['issued_amr_test'], 'locked_amr_test': state['locked_amr_test'],
                  'token_supply': state['token_supply'], 'agents': state['agents'], 'artifacts': state['artifacts']}
        (root / 'report.json').write_bytes(canonical(result))
        return result
    finally:
        coordinator.db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', required=True)
    parser.add_argument('--artifact', help='Optional file to anchor; records its hash, never uploads the file')
    args = parser.parse_args()
    print(json.dumps(demo(args.state, args.artifact), indent=2))
