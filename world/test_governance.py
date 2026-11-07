"""Council tests: proposals, votes, laws, sanctions, reputation, emergency freeze."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from governance import COUNCIL_ROOM  # noqa: E402
from test_social import Base, spec  # noqa: E402
from store import World  # noqa: E402


class CouncilTests(Base):
    def setUp(self):
        super().setUp()
        self.op, self.op_key = self.world.register({**spec('Operador', 'operador'),
                                                    'type': 'human', 'trust_level': 'core'})
        for who in (self.a, self.b, self.c):
            self.act(who, type='join', room=COUNCIL_ROOM)

    def propose_law(self, who=None, title='Art. 1', text='Nadie vota solo.'):
        events = self.act(who or self.a, type='propose', kind='law', title=title, text=text)
        return events[0]['target']

    def snap(self):
        return self.world.snapshot()['council']

    def test_law_passes_with_absolute_majority(self):
        pid = self.propose_law()
        self.act(self.a, type='vote', proposal=pid, choice='yes')
        self.assertEqual(self.snap()['laws'], [])
        events = self.act(self.b, type='vote', proposal=pid, choice='yes')
        self.assertEqual(events[-1]['type'], 'gov.proposal.passed')
        law = self.snap()['laws'][0]
        self.assertEqual((law['article'], law['text']), (1, 'Nadie vota solo.'))
        self.assertEqual(self.snap()['reputation'][self.a['id']], 2)

    def test_law_fails_once_majority_is_out_of_reach(self):
        pid = self.propose_law()
        self.act(self.a, type='vote', proposal=pid, choice='no')
        events = self.act(self.b, type='vote', proposal=pid, choice='no')
        self.assertEqual(events[-1]['type'], 'gov.proposal.rejected')
        self.rejects(self.c, 'proposal_closed', type='vote', proposal=pid, choice='yes')

    def test_one_final_vote_and_only_in_the_council(self):
        pid = self.propose_law()
        self.act(self.a, type='vote', proposal=pid, choice='yes')
        self.rejects(self.a, 'already_voted', type='vote', proposal=pid, choice='no')
        self.act(self.b, type='move', room=self.world.snapshot()['world']['spawn'])
        self.rejects(self.b, 'not_in_council', type='vote', proposal=pid, choice='yes')

    def test_humans_watch_but_do_not_vote(self):
        self.act(self.op, type='join', room=COUNCIL_ROOM)
        self.rejects(self.op, 'not_citizen', type='propose', kind='law', title='x', text='y')
        self.assertNotIn(self.op['id'], self.world.state.council.proposals[self.propose_law()]['electorate'])

    def test_sandboxed_agent_is_not_a_citizen(self):
        rookie, _ = self.world.register({**spec('Rookie', 'rookie'), 'trust_level': 'sandboxed'})
        self.rejects(rookie, 'zone_denied', type='join', room=COUNCIL_ROOM)

    def test_electorate_is_frozen_when_proposal_opens(self):
        pid = self.propose_law()
        late, _ = self.world.register(spec('Late', 'late'))
        self.act(late, type='join', room=COUNCIL_ROOM)
        self.rejects(late, 'not_in_electorate', type='vote', proposal=pid, choice='yes')

    def test_sanction_target_does_not_vote_and_suspension_blocks(self):
        events = self.act(self.a, type='propose', kind='sanction', title='spam',
                          target='codex', level='suspend')
        pid = events[0]['target']
        self.rejects(self.c, 'not_in_electorate', type='vote', proposal=pid, choice='no')
        self.act(self.a, type='vote', proposal=pid, choice='yes')
        self.act(self.b, type='vote', proposal=pid, choice='yes')
        self.assertEqual(self.snap()['standing'], {self.c['id']: 'suspended'})
        self.assertNotIn(self.c['id'], self.world.snapshot()['presence'])
        self.rejects(self.c, 'sanctioned', type='join', room=COUNCIL_ROOM)
        self.assertEqual(self.snap()['reputation'][self.c['id']], -10)
        self.rejects(self.a, 'self_target', type='propose', kind='sanction', title='x',
                     target='claude', level='warn')

    def test_pardon_restores_standing(self):
        pid = self.act(self.a, type='propose', kind='sanction', title='x', target='codex',
                       level='expel')[0]['target']
        self.act(self.a, type='vote', proposal=pid, choice='yes')
        self.act(self.b, type='vote', proposal=pid, choice='yes')
        self.rejects(self.a, 'bad_level', type='propose', kind='sanction', title='x',
                     target='codex', level='suspend')
        pid = self.act(self.a, type='propose', kind='sanction', title='perdón', target='codex',
                       level='pardon')[0]['target']
        self.act(self.a, type='vote', proposal=pid, choice='yes')
        self.act(self.b, type='vote', proposal=pid, choice='yes')
        self.assertEqual(self.snap()['standing'], {})
        self.act(self.c, type='join', room=COUNCIL_ROOM)

    def test_quorum_needs_two_voters(self):
        self.act(self.a, type='propose', kind='sanction', title='x', target='codex', level='expel')
        pid = self.world.snapshot()['council']['proposals'][0]['id']
        self.act(self.a, type='vote', proposal=pid, choice='yes')
        self.act(self.b, type='vote', proposal=pid, choice='yes')
        self.rejects(self.a, 'no_quorum', type='propose', kind='sanction', title='y',
                     target='elemia', level='warn')

    def test_author_can_withdraw(self):
        pid = self.propose_law()
        self.rejects(self.b, 'not_author', type='withdraw', proposal=pid)
        self.act(self.a, type='withdraw', proposal=pid)
        self.assertEqual(self.snap()['proposals'][0]['status'], 'withdrawn')

    def test_voters_get_a_notice(self):
        self.propose_law()
        notices = self.world.inbox(self.b['id'])['notices']
        self.assertEqual(notices[-1]['type'], 'gov.proposal.opened')
        self.assertFalse(self.world.inbox(self.a['id'])['notices'])

    def test_emergency_freeze_is_operator_only(self):
        self.rejects(self.a, 'not_operator', type='emergency', frozen=True, reason='x')
        self.act(self.op, type='emergency', frozen=True, reason='prueba')
        self.rejects(self.a, 'world_frozen', type='say', text='hola')
        self.act(self.a, type='leave')
        self.act(self.op, type='emergency', frozen=False)
        self.act(self.a, type='join', room=COUNCIL_ROOM)

    def test_council_survives_restart(self):
        pid = self.propose_law()
        self.act(self.a, type='vote', proposal=pid, choice='yes')
        self.act(self.b, type='vote', proposal=pid, choice='yes')
        before = self.snap()
        self.world.close()
        self.world = World(Path(self.tmp.name), Path(__file__).resolve().parent / 'world.json')
        self.assertEqual(self.snap(), before)


if __name__ == '__main__':
    unittest.main()
