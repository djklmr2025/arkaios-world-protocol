"""Run the local WAV circuit and four-validator testnet, then verify a restart.

Only the WAV hash connects the demonstrations. Their identities and synthetic
balances remain separate. No external services or credentials are used.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
CIRCUIT = ROOT / 'simulator' / 'agent_economy'
TESTNET = ROOT / 'testnet'


def run_json(script, *args):
    result = subprocess.run([sys.executable, str(script), *map(str, args)],
                            cwd=script.parent, capture_output=True, text=True,
                            encoding='utf-8', check=True, timeout=180)
    return json.loads(result.stdout)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_pair(circuit, network, artifact):
    audio_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
    require(circuit['mode'] == 'LOCAL_SYNTHETIC_PAYMENT' and circuit['task'] == 'ACCEPTED',
            'circuit task was not accepted')
    require(circuit['delivery']['audio_hash'] == audio_hash, 'delivery hash mismatch')
    require(circuit['buyer_balance'] == [750, 0] and circuit['agent_balance'] == [250, 0],
            'unexpected circuit balances')
    require(network['mode'] == 'TEST_ONLY', 'not a test network')
    require(network['validators'] == 4 and network['quorum'] == 3 and network['blocks'] == 4,
            'unexpected validator or block count')
    require(network['max_block_bytes'] == 8_000_000, 'unexpected block limit')
    require(network['issued_amr_test'] == 1000 and
            network['locked_amr_test'] == network['token_supply'] == 350,
            'unexpected test backing')
    anchors = list(network['artifacts'].values())
    require(len(anchors) == 1 and anchors[0]['sha256'] == audio_hash, 'artifact anchor mismatch')
    return audio_hash


def main(state, music_root):
    state = Path(state).resolve()
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Remove an old success marker before work, so failed runs cannot look current.
    report_path = state / 'pilot-report.json'
    report_path.unlink(missing_ok=True)
    # Check pinned bytes even on a restart that would reuse an existing WAV.
    sys.path.insert(0, str(CIRCUIT))
    from circuit import MUSIC_COMMIT, SOURCE_HASHES
    music_root = Path(music_root).resolve()
    for relative, expected in SOURCE_HASHES.items():
        source = music_root / relative
        require(not source.is_symlink() and source.is_file() and
                hashlib.sha256(source.read_bytes()).hexdigest() == expected,
                'music source mismatch: ' + relative)
    artifact = state / 'circuit' / 'artifacts' / 'render-001' / 'delivery.wav'
    print('1/4 Render and synthetic acceptance', flush=True)
    first = run_json(CIRCUIT / 'circuit.py', '--state', state / 'circuit', '--music-root', music_root)
    print('2/4 Certify WAV hash with four local validators', flush=True)
    network = run_json(TESTNET / 'network.py', '--state', state / 'testnet', '--artifact', artifact)
    audio_hash = verify_pair(first, network, artifact)
    print('3/4 Reopen circuit and network without duplicate payments', flush=True)
    again = run_json(CIRCUIT / 'circuit.py', '--state', state / 'circuit', '--music-root', music_root)
    reopened = run_json(TESTNET / 'network.py', '--state', state / 'testnet', '--artifact', artifact)
    require(verify_pair(again, reopened, artifact) == audio_hash, 'artifact changed on restart')
    for field in ('delivery', 'buyer_balance', 'agent_balance', 'audit'):
        require(first[field] == again[field], 'circuit changed on restart: ' + field)
    require(network == reopened, 'network changed on restart')
    require(again['recovered_memories'] >= 2, 'signed memories were not recovered')
    report = {'mode': 'TEST_ONLY', 'verified_restart': True, 'music_commit': MUSIC_COMMIT,
              'audio_sha256': audio_hash, 'circuit': again, 'testnet': reopened,
              'connection': 'ARTIFACT_HASH_ONLY', 'external_services_used': False}
    temporary = report_path.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(temporary, report_path)
    print('4/4 PASS - report: ' + str(report_path), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', default=str(ROOT / '.local-pilot'))
    parser.add_argument('--music-root', required=True)
    args = parser.parse_args()
    try:
        main(args.state, args.music_root)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print('Pilot FAILED: ' + str(exc), file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            print(exc.stderr[-4000:], file=sys.stderr)
        raise SystemExit(1)
