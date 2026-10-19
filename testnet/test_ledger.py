import copy
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ledger import (Node, MAX_BLOCK_BYTES, apply_tx, canonical, certify, genesis,
                    hashed, initial_state, public, registration, sign_tx, size_guard, agent_id)
from network import LoopbackNetwork, call, demo


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.registrar, self.buyer, self.seller, self.child = [Ed25519PrivateKey.generate() for _ in range(4)]
        self.keys = {n: Ed25519PrivateKey.generate() for n in ('v1','v2','v3','v4')}
        self.config = genesis('test', public(self.registrar), {n: public(k) for n,k in self.keys.items()})
        self.nodes = [Node(self.root / (n+'.sqlite'), self.config, n, k) for n,k in self.keys.items()]

    def tearDown(self):
        for node in self.nodes:
            node.db.close()
        self.tmp.cleanup()

    def commit(self, transactions):
        envelope = certify(self.nodes[0], self.nodes, transactions)
        for node in self.nodes:
            node.commit(envelope)
        return envelope

    def registered(self):
        return self.commit([registration(self.config,self.registrar,'registrar',1,self.buyer),
                            registration(self.config,self.registrar,'registrar',2,self.seller)])

    def test_lineage_global_serial_and_child_order(self):
        self.registered()
        self.commit([registration(self.config,self.seller,agent_id(self.config,2),1,self.child),
                     registration(self.config,self.buyer,agent_id(self.config,1),1,Ed25519PrivateKey.generate()),
                     registration(self.config,self.seller,agent_id(self.config,2),2,Ed25519PrivateKey.generate())])
        state,_,_ = self.nodes[0].state()
        self.assertEqual(list(state['agents']), [agent_id(self.config,1),agent_id(self.config,2),agent_id(self.config,3),agent_id(self.config,4),agent_id(self.config,5)])
        self.assertEqual(state['agents'][agent_id(self.config,3)]['parent'],agent_id(self.config,2))
        self.assertEqual(state['agents'][agent_id(self.config,5)]['child_index'],2)
        self.assertEqual(state['agents'][agent_id(self.config,3)]['generation'],1)
        self.assertEqual(state['issued_amr_test'],0)

    def test_redeem_transferred_token_and_backing(self):
        self.registered()
        self.commit([sign_tx(self.config,self.registrar,'registrar',3,'test.fund',{'recipient':agent_id(self.config,1),'amount':1000}),
                     sign_tx(self.config,self.buyer,agent_id(self.config,1),1,'bridge.lock_mint',{'amount':600})])
        self.commit([sign_tx(self.config,self.buyer,agent_id(self.config,1),2,'token.transfer',{'recipient':agent_id(self.config,2),'amount':250}),
                     sign_tx(self.config,self.seller,agent_id(self.config,2),1,'bridge.burn_redeem',{'amount':250})])
        state,_,_=self.nodes[0].state()
        self.assertEqual(state['locked_amr_test'],350)
        self.assertEqual(state['token_supply'],350)
        self.assertEqual(state['agents'][agent_id(self.config,2)]['amr_test'],250)

    def test_unfunded_mint_and_double_spend_rejected(self):
        self.registered()
        for op in ('bridge.lock_mint','bridge.burn_redeem'):
            with self.assertRaises(ValueError):
                self.nodes[0].propose([sign_tx(self.config,self.buyer,agent_id(self.config,1),1,op,{'amount':1})])
        self.commit([sign_tx(self.config,self.registrar,'registrar',3,'test.fund',{'recipient':agent_id(self.config,1),'amount':10}),
                     sign_tx(self.config,self.buyer,agent_id(self.config,1),1,'bridge.lock_mint',{'amount':10})])
        with self.assertRaises(ValueError):
            self.nodes[0].propose([sign_tx(self.config,self.buyer,agent_id(self.config,1),2,'token.transfer',{'recipient':agent_id(self.config,2),'amount':7}),
                                  sign_tx(self.config,self.buyer,agent_id(self.config,1),3,'token.transfer',{'recipient':agent_id(self.config,2),'amount':7})])
        self.assertEqual(self.nodes[0].state()[0]['agents'][agent_id(self.config,1)]['token'],10)

    def test_quorum_and_certificate_tampering(self):
        envelope = certify(self.nodes[0], self.nodes, [registration(self.config,self.registrar,'registrar',1,self.buyer)])
        bad=copy.deepcopy(envelope)
        bad['signatures']={k:v for k,v in list(bad['signatures'].items())[:2]}
        with self.assertRaises(ValueError):self.nodes[0].commit(bad)
        bad=copy.deepcopy(envelope)
        bad['body']['state_hash']='0'*64
        with self.assertRaises(InvalidSignature):self.nodes[0].commit(bad)
        self.assertEqual(self.nodes[0].state()[1],1)

    def test_replay_other_chain_and_invalid_signature(self):
        tx=registration(self.config,self.registrar,'registrar',1,self.buyer)
        self.commit([tx])
        with self.assertRaises(ValueError):self.nodes[0].propose([tx])
        other=copy.deepcopy(self.config);other['chain_id']='other'
        with self.assertRaises(ValueError):apply_tx(initial_state(),tx,other)
        forged=registration(self.config,self.buyer,'registrar',2,self.seller)
        with self.assertRaises(InvalidSignature):self.nodes[0].propose([forged])

    def test_vote_lock_survives_restart(self):
        a=self.nodes[0].propose([registration(self.config,self.registrar,'registrar',1,self.buyer)])
        b=self.nodes[0].propose([registration(self.config,self.registrar,'registrar',1,self.seller)])
        sig=self.nodes[0].vote(a)
        self.nodes[0].db.close()
        self.nodes[0]=Node(self.root/'v1.sqlite',self.config,'v1',self.keys['v1'])
        self.assertEqual(self.nodes[0].vote(a),sig)
        with self.assertRaisesRegex(ValueError,'already voted'):self.nodes[0].vote(b)

    def test_one_offline_replica_catches_up_and_replay_is_idempotent(self):
        envelope=certify(self.nodes[0],self.nodes[:3],[registration(self.config,self.registrar,'registrar',1,self.buyer)])
        for node in self.nodes[:3]:node.commit(envelope)
        self.assertEqual(self.nodes[3].state()[1],1)
        self.nodes[3].commit(envelope)
        self.nodes[3].commit(envelope)
        roots={hashed(n.state()[0]) for n in self.nodes}
        self.assertEqual(len(roots),1)

    def test_disk_tamper_detected(self):
        self.registered()
        self.nodes[0].db.execute("UPDATE blocks SET hash=? WHERE height=1",('0'*64,))
        with self.assertRaisesRegex(ValueError,'stored chain mismatch'):self.nodes[0].state()

    def test_block_byte_boundaries(self):
        size_guard(b' '*(MAX_BLOCK_BYTES-1))
        size_guard(b' '*MAX_BLOCK_BYTES)
        with self.assertRaises(ValueError):size_guard(b' '*(MAX_BLOCK_BYTES+1))

    def test_same_display_chain_name_has_distinct_genesis_namespace(self):
        other=copy.deepcopy(self.config)
        other['registrar_key']=public(Ed25519PrivateKey.generate())
        self.assertNotEqual(agent_id(self.config,1),agent_id(other,1))

    def test_nonce_bool_unknown_fields_and_duplicate_key(self):
        self.registered()
        for amount in (True,-1,0,1.2):
            tx=sign_tx(self.config,self.registrar,'registrar',3,'test.fund',{'recipient':agent_id(self.config,1),'amount':amount})
            with self.assertRaises(ValueError):self.nodes[0].propose([tx])
        with self.assertRaisesRegex(ValueError,'already registered'):
            self.nodes[0].propose([registration(self.config,self.registrar,'registrar',3,self.buyer)])
        with self.assertRaisesRegex(ValueError,'nonce mismatch'):
            self.nodes[0].propose([registration(self.config,self.registrar,'registrar',True,self.child)])

    def test_loopback_http_real_processes(self):
        # Separate paths from the direct-node test fixture.
        with LoopbackNetwork(self.root/'http',self.config,self.keys) as network:
            body=self.nodes[0].propose([registration(self.config,self.registrar,'registrar',1,self.buyer)])
            envelope,receipts=network.finalize(body,voters=['v1','v2','v3'])
            self.assertEqual(len(receipts),4)
            status=[call(p,'/status') for p in network.ports.values()]
            self.assertEqual({s['next_height'] for s in status},{2})
            bad=copy.deepcopy(envelope);bad['body']['previous']='0'*64
            with self.assertRaises(urllib.error.HTTPError):call(network.ports['v4'],'/commit',bad)

    def test_network_demo_restart_preserves_supply(self):
        root=self.root/'demo'
        a=demo(root)
        b=demo(root)
        self.assertEqual(a['state_hash'],b['state_hash'])
        self.assertEqual(a['issued_amr_test'],1000)
        self.assertEqual(b['token_supply'],350)

    def test_artifact_anchor_and_changed_file_rejection(self):
        root=self.root/'artifact-demo'
        artifact=self.root/'delivery.wav'
        artifact.write_bytes(b'test-artifact-not-an-audio-validation')
        first=demo(root,artifact)
        second=demo(root,artifact)
        self.assertEqual(first['blocks'],4)
        self.assertEqual(first['state_hash'],second['state_hash'])
        artifact.write_bytes(b'altered')
        with self.assertRaisesRegex(ValueError,'anchored artifact differs'):demo(root,artifact)


if __name__=='__main__':unittest.main()
