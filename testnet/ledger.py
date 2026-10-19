"""Permissioned test ledger. Test assets only; fixed validators; no view change."""
import copy
import hashlib
import json
from pathlib import Path
import re
import sqlite3

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MAX_BLOCK_BYTES = 8_000_000
MAX_TX_BYTES = 65_536
MAX_AMOUNT = 10**12


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def hashed(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def public(key):
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def verify(key_hex, message, signature):
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(key_hex)).verify(bytes.fromhex(signature), message)


def size_guard(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_BLOCK_BYTES:
        raise ValueError('block exceeds 8000000 bytes')


def positive(value):
    if type(value) is not int or not 0 < value <= MAX_AMOUNT:
        raise ValueError('amount must be positive integer test minor units')


def exact_keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError('unexpected fields')


def genesis(chain_id, registrar_key, validators):
    if not isinstance(chain_id, str) or not 1 <= len(chain_id) <= 64 or ':' in chain_id:
        raise ValueError('invalid chain id')
    if len(validators) != 4 or len(set(validators.values())) != 4:
        raise ValueError('four independent validator public keys required')
    if any(not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', name) for name in validators):
        raise ValueError('invalid validator id')
    for key in [registrar_key, *validators.values()]:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(key))
    return {'protocol': 'ark-testnet-v1', 'chain_id': chain_id, 'registrar_key': registrar_key,
            'validators': dict(validators), 'quorum': 3, 'max_block_bytes': MAX_BLOCK_BYTES,
            'asset_mode': 'TEST_ONLY_1_TO_1_AMR_TEST', 'state_schema': 'identity-wallet-artifact-v1'}


def initial_state():
    return {'next_serial': 1, 'agents': {}, 'nonces': {'registrar': 0}, 'txids': [],
            'issued_amr_test': 0, 'token_supply': 0, 'locked_amr_test': 0, 'artifacts': {}}


def sign_tx(config, key, actor, nonce, operation, payload):
    message = {'domain': 'ark.test.tx.v1', 'genesis': hashed(config), 'actor': actor,
               'nonce': nonce, 'operation': operation, 'payload': payload}
    return {'message': message, 'signature': key.sign(canonical(message)).hex()}


def registration(config, controller, actor, nonce, child_key):
    payload = {'public_key': public(child_key)}
    proof = {'domain': 'ark.test.child.v1', 'genesis': hashed(config),
             'actor': actor, 'nonce': nonce, 'public_key': payload['public_key']}
    payload['child_proof'] = child_key.sign(canonical(proof)).hex()
    return sign_tx(config, controller, actor, nonce, 'agent.register', payload)


def apply_tx(state, tx, config):
    if len(canonical(tx)) > MAX_TX_BYTES:
        raise ValueError('transaction too large')
    exact_keys(tx, ['message', 'signature'])
    m = tx['message']
    exact_keys(m, ['domain', 'genesis', 'actor', 'nonce', 'operation', 'payload'])
    if m['domain'] != 'ark.test.tx.v1' or m['genesis'] != hashed(config):
        raise ValueError('wrong chain or transaction domain')
    txid = hashed(tx)
    if txid in state['txids']:
        raise ValueError('duplicate transaction')
    actor, payload = m['actor'], m['payload']
    if not isinstance(actor, str) or actor not in state['nonces']:
        raise ValueError('unknown actor')
    if type(m['nonce']) is not int or m['nonce'] != state['nonces'][actor] + 1:
        raise ValueError('nonce mismatch')
    key = config['registrar_key'] if actor == 'registrar' else state['agents'][actor]['public_key']
    verify(key, canonical(m), tx['signature'])
    op = m['operation']
    if op == 'agent.register':
        exact_keys(payload, ['public_key', 'child_proof'])
        if payload['public_key'] == config['registrar_key'] or any(a['public_key'] == payload['public_key'] for a in state['agents'].values()):
            raise ValueError('key already registered')
        proof = {'domain': 'ark.test.child.v1', 'genesis': hashed(config), 'actor': actor,
                 'nonce': m['nonce'], 'public_key': payload['public_key']}
        verify(payload['public_key'], canonical(proof), payload['child_proof'])
        serial = state['next_serial']
        identity = config['chain_id'] + ':' + str(serial)
        parent = None if actor == 'registrar' else actor
        child_index = 0
        if parent:
            state['agents'][parent]['children'] += 1
            child_index = state['agents'][parent]['children']
        state['agents'][identity] = {'public_key': payload['public_key'], 'parent': parent,
            'child_index': child_index, 'children': 0,
            'generation': 0 if parent is None else state['agents'][parent]['generation'] + 1,
            'amr_test': 0, 'token': 0, 'locked': 0}
        state['nonces'][identity] = 0
        state['next_serial'] += 1
    elif op == 'test.fund':
        exact_keys(payload, ['recipient', 'amount'])
        positive(payload['amount'])
        if actor != 'registrar':
            raise ValueError('test faucet requires registrar')
        account = state['agents'][payload['recipient']]
        if account['amr_test'] + payload['amount'] > MAX_AMOUNT:
            raise ValueError('account limit')
        account['amr_test'] += payload['amount']
        state['issued_amr_test'] += payload['amount']
    elif op in ('bridge.lock_mint', 'bridge.burn_redeem'):
        exact_keys(payload, ['amount'])
        positive(payload['amount'])
        if actor == 'registrar':
            raise ValueError('agent account required')
        account, amount = state['agents'][actor], payload['amount']
        if op == 'bridge.lock_mint':
            if account['amr_test'] < amount:
                raise ValueError('insufficient AMR_TEST')
            account['amr_test'] -= amount
            account['locked'] += amount
            account['token'] += amount
            state['token_supply'] += amount
            state['locked_amr_test'] += amount
        else:
            if account['token'] < amount or state['locked_amr_test'] < amount:
                raise ValueError('insufficient redeemable test assets')
            # Reserves back the common token pool, not only its original minter.
            remaining = amount
            for owner in sorted(state['agents']):
                locked = state['agents'][owner]['locked']
                used = min(locked, remaining)
                state['agents'][owner]['locked'] -= used
                remaining -= used
                if remaining == 0:
                    break
            account['token'] -= amount
            account['amr_test'] += amount
            state['token_supply'] -= amount
            state['locked_amr_test'] -= amount
    elif op == 'artifact.anchor':
        exact_keys(payload, ['sha256', 'task_ref'])
        if actor == 'registrar' or not isinstance(payload['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', payload['sha256']):
            raise ValueError('agent and SHA-256 required')
        if not isinstance(payload['task_ref'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', payload['task_ref']):
            raise ValueError('invalid task reference')
        reference = actor + ':' + payload['task_ref']
        if reference in state['artifacts']:
            raise ValueError('artifact task already anchored')
        state['artifacts'][reference] = {'agent': actor, 'sha256': payload['sha256'], 'txid': txid}
    elif op == 'token.transfer':
        exact_keys(payload, ['recipient', 'amount'])
        positive(payload['amount'])
        if actor == 'registrar' or payload['recipient'] == actor:
            raise ValueError('distinct agent accounts required')
        sender, recipient = state['agents'][actor], state['agents'][payload['recipient']]
        if sender['token'] < payload['amount']:
            raise ValueError('insufficient token')
        sender['token'] -= payload['amount']
        recipient['token'] += payload['amount']
    else:
        raise ValueError('unsupported operation')
    for a in state['agents'].values():
        if any(type(a[k]) is not int or not 0 <= a[k] <= MAX_AMOUNT for k in ('amr_test', 'token', 'locked')):
            raise ValueError('invalid account amount')
    state['nonces'][actor] = m['nonce']
    state['txids'].append(txid)
    audit(state)


def audit(state):
    agents = list(state['agents'].values())
    if sum(a['amr_test'] + a['locked'] for a in agents) != state['issued_amr_test']:
        raise ValueError('AMR_TEST conservation failure')
    if sum(a['token'] for a in agents) != state['token_supply']:
        raise ValueError('token conservation failure')
    if sum(a['locked'] for a in agents) != state['locked_amr_test'] or state['token_supply'] != state['locked_amr_test']:
        raise ValueError('test token backing failure')


class Node:
    def __init__(self, db_path, config, validator_id, key):
        if config != genesis(config['chain_id'], config['registrar_key'], config['validators']):
            raise ValueError('unsupported genesis configuration')
        if public(key) != config['validators'].get(validator_id):
            raise ValueError('validator key mismatch')
        self.config, self.validator_id, self.key = copy.deepcopy(config), validator_id, key
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(db_path), isolation_level=None)
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS config(id INTEGER PRIMARY KEY CHECK(id=1), genesis TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS blocks(height INTEGER PRIMARY KEY, hash TEXT UNIQUE NOT NULL, envelope TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS votes(height INTEGER PRIMARY KEY, hash TEXT NOT NULL, signature TEXT NOT NULL);
        ''')
        existing = self.db.execute('SELECT genesis FROM config WHERE id=1').fetchone()
        if existing and existing[0] != canonical(config).decode():
            raise ValueError('database belongs to a different genesis')
        self.db.execute('INSERT OR IGNORE INTO config VALUES (1,?)', (canonical(config).decode(),))

    def certificate(self, body, signatures):
        if not isinstance(signatures, dict) or not self.config['quorum'] <= len(signatures) <= 4:
            raise ValueError('quorum of distinct validators required')
        message = b'ARK_TEST_BLOCK_V1:' + canonical(body)
        for validator, sig in signatures.items():
            if validator not in self.config['validators']:
                raise ValueError('unknown validator')
            verify(self.config['validators'][validator], message, sig)

    def transition(self, state, body, height, previous):
        exact_keys(body, ['protocol', 'genesis', 'height', 'previous', 'transactions', 'state_hash'])
        if body['protocol'] != 'ark-testnet-v1' or body['genesis'] != hashed(self.config):
            raise ValueError('wrong block domain')
        if type(body['height']) is not int or body['height'] != height or body['previous'] != previous:
            raise ValueError('block does not extend current tip')
        if not isinstance(body['transactions'], list) or not 1 <= len(body['transactions']) <= 100:
            raise ValueError('bounded nonempty transaction list required')
        next_state = copy.deepcopy(state)
        for tx in body['transactions']:
            apply_tx(next_state, tx, self.config)
        if hashed(next_state) != body['state_hash']:
            raise ValueError('state root mismatch')
        return next_state

    def state(self):
        state, previous, height = initial_state(), hashed(self.config), 1
        for stored_height, block_hash, raw in self.db.execute('SELECT height,hash,envelope FROM blocks ORDER BY height'):
            size_guard(raw.encode())
            envelope = json.loads(raw)
            exact_keys(envelope, ['body', 'signatures'])
            body = envelope['body']
            self.certificate(body, envelope['signatures'])
            if stored_height != height or hashed(body) != block_hash:
                raise ValueError('stored chain mismatch')
            state = self.transition(state, body, height, previous)
            previous, height = block_hash, height + 1
        return state, height, previous

    def propose(self, transactions):
        state, height, previous = self.state()
        next_state = copy.deepcopy(state)
        for tx in transactions:
            apply_tx(next_state, tx, self.config)
        body = {'protocol': 'ark-testnet-v1', 'genesis': hashed(self.config), 'height': height,
                'previous': previous, 'transactions': transactions, 'state_hash': hashed(next_state)}
        self.transition(state, body, height, previous)
        return body

    def vote(self, body):
        # Reserve enough room for all validator signatures before signing.
        size_guard(canonical({'body': body, 'signatures': {k: '0' * 128 for k in self.config['validators']}}))
        self.db.execute('BEGIN IMMEDIATE')
        try:
            state, height, previous = self.state()
            self.transition(state, body, height, previous)
            block_hash = hashed(body)
            existing = self.db.execute('SELECT hash,signature FROM votes WHERE height=?', (height,)).fetchone()
            if existing and existing[0] != block_hash:
                raise ValueError('validator already voted for another block at this height')
            sig = existing[1] if existing else self.key.sign(b'ARK_TEST_BLOCK_V1:' + canonical(body)).hex()
            self.db.execute('INSERT OR IGNORE INTO votes VALUES (?,?,?)', (height, block_hash, sig))
            self.db.execute('COMMIT')
            return sig
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def commit(self, envelope):
        raw = canonical(envelope)
        size_guard(raw)
        exact_keys(envelope, ['body', 'signatures'])
        body = envelope['body']
        self.certificate(body, envelope['signatures'])
        self.db.execute('BEGIN IMMEDIATE')
        try:
            block_hash = hashed(body)
            old = self.db.execute('SELECT hash FROM blocks WHERE height=?', (body['height'],)).fetchone()
            if old:
                if old[0] != block_hash:
                    raise ValueError('conflicting finalized block')
                # Re-audit even idempotent delivery.
                self.state()
            else:
                state, height, previous = self.state()
                self.transition(state, body, height, previous)
                self.db.execute('INSERT INTO blocks VALUES (?,?,?)', (height, block_hash, raw.decode()))
            self.db.execute('COMMIT')
            return block_hash
        except BaseException:
            self.db.execute('ROLLBACK')
            raise


def certify(proposer, nodes, transactions):
    body = proposer.propose(transactions)
    signatures = {node.validator_id: node.vote(body) for node in nodes}
    envelope = {'body': body, 'signatures': signatures}
    proposer.certificate(body, signatures)
    return envelope
