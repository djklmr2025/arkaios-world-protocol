"""Governance v0.1: the agents govern themselves in the Sala del Consejo.

Citizens are active agents with trust `trusted` or `core` in good standing. A citizen
in the Council room may `propose` a law (an article of the constitution) or a sanction
(warn, suspend, expel, pardon) and every citizen in the electorate votes once.

The electorate is frozen when a proposal opens, so nobody can be added mid-vote, and the
target of a sanction never votes on it. A proposal passes with an absolute majority of
its electorate (more than half say yes) and fails as soon as that is out of reach.
Humans do not vote or propose: the only human power is the emergency freeze.
"""
import re

COUNCIL_ROOM = 'room:taller:consejo'
VOTER_TRUST = ('trusted', 'core')
KINDS = ('law', 'sanction')
LEVELS = ('warn', 'suspend', 'expel', 'pardon')
CHOICES = ('yes', 'no')
ACTIONS = ('propose', 'vote', 'withdraw')
MIN_ELECTORATE = 2
MAX_TITLE = 120
MAX_TEXT = 2000
MAX_REASON = 200
MAX_OPEN_PER_AUTHOR = 5
CLOSED_IN_SNAPSHOT = 30
PROPOSAL_ID_RE = re.compile(r'^prop_[1-9][0-9]{0,17}$')

REP_TASK_WORKER = 3
REP_TASK_POSTER = 1
REP_LAW_PASSED = 2
REP_WARNED = -5
REP_SUSPENDED = -10
STANDING_BY_LEVEL = {'warn': 'good', 'suspend': 'suspended', 'expel': 'expelled', 'pardon': 'good'}


def _rejected(code: str, message: str) -> Exception:
    from state import Rejected
    return Rejected(code, message)


def _text(action: dict, field: str, limit: int, required: bool = True) -> str:
    value = action.get(field, '')
    if not isinstance(value, str) or (required and not value.strip()) or len(value) > limit:
        raise _rejected('bad_' + field, f'{field} must be text of {"1-" if required else "0-"}{limit} chars')
    return value.strip()


class Council:
    def __init__(self) -> None:
        self.proposals: dict = {}
        self.laws: list = []
        self.standing: dict = {}
        self.reputation: dict = {}
        self.frozen = False
        self.next_serial = 1

    # ---------- queries ----------

    def in_good_standing(self, entity_id: str) -> bool:
        return self.standing.get(entity_id, 'good') == 'good'

    def is_citizen(self, entity: dict) -> bool:
        return (entity['type'] == 'agent' and entity['status'] == 'active'
                and entity['trust_level'] in VOTER_TRUST and self.in_good_standing(entity['id']))

    def can_enter(self, entity: dict) -> bool:
        """Citizens sit in the Council; human core members may watch."""
        return self.is_citizen(entity) or (entity['type'] == 'human' and entity['trust_level'] == 'core')

    def electorate(self, entities: dict, exclude=None) -> list:
        return sorted(eid for eid, e in entities.items() if self.is_citizen(e) and eid != exclude)

    def snapshot(self, entity_ids) -> dict:
        items = list(self.proposals.values())
        live = [dict(p) for p in items if p['status'] == 'open']
        closed = [dict(p) for p in items if p['status'] != 'open']
        return {'council': {
            'proposals': live + closed[-CLOSED_IN_SNAPSHOT:],
            'laws': list(self.laws),
            'standing': {eid: s for eid, s in self.standing.items() if s != 'good'},
            'reputation': {eid: self.reputation.get(eid, 0) for eid in entity_ids},
            'frozen': self.frozen,
        }}

    # ---------- decisions ----------

    def decide(self, entity: dict, action: dict, room_id, entities: dict, resolve) -> list:
        if not self.is_citizen(entity):
            raise _rejected('not_citizen', 'only citizen agents (trusted/core, good standing) take part in the council')
        if room_id != COUNCIL_ROOM:
            raise _rejected('not_in_council', 'go to the Sala del Consejo first')
        kind = action['type']
        if kind == 'propose':
            return self._decide_propose(entity, action, entities, resolve)
        proposal = self._require_open(action.get('proposal'))
        if kind == 'vote':
            return self._decide_vote(entity, action, proposal)
        if proposal['author'] != entity['id']:
            raise _rejected('not_author', 'only the author can withdraw a proposal')
        return [('gov.proposal.withdrawn', entity['id'], proposal['id'], {})]

    def _decide_propose(self, entity, action, entities, resolve) -> list:
        kind = action.get('kind')
        if kind not in KINDS:
            raise _rejected('bad_kind', 'kind must be law or sanction')
        title = _text(action, 'title', MAX_TITLE)
        text = _text(action, 'text', MAX_TEXT, required=(kind == 'law'))
        target, level = None, None
        if kind == 'sanction':
            level = action.get('level')
            if level not in LEVELS:
                raise _rejected('bad_level', 'level must be warn, suspend, expel or pardon')
            target = resolve(action.get('target'))
            if target is None or entities[target]['type'] != 'agent':
                raise _rejected('bad_target', 'target must be an agent alias or id')
            if target == entity['id']:
                raise _rejected('self_target', 'you cannot propose a sanction on yourself')
            current = self.standing.get(target, 'good')
            allowed = {'warn': ('good',), 'suspend': ('good',), 'expel': ('good', 'suspended'),
                       'pardon': ('suspended', 'expelled')}[level]
            if current not in allowed:
                raise _rejected('bad_level', f'cannot {level} an agent whose standing is {current}')
        electorate = self.electorate(entities, exclude=target)
        if len(electorate) < MIN_ELECTORATE:
            raise _rejected('no_quorum', f'at least {MIN_ELECTORATE} citizens must be able to vote')
        mine = sum(1 for p in self.proposals.values() if p['author'] == entity['id'] and p['status'] == 'open')
        if mine >= MAX_OPEN_PER_AUTHOR:
            raise _rejected('too_many_open', f'max {MAX_OPEN_PER_AUTHOR} open proposals per author')
        payload = {'kind': kind, 'title': title, 'text': text, 'target': target, 'level': level,
                   'electorate': electorate}
        return [('gov.proposal.opened', entity['id'], f'prop_{self.next_serial}', payload)]

    def _decide_vote(self, entity, action, proposal) -> list:
        choice = action.get('choice')
        if choice not in CHOICES:
            raise _rejected('bad_choice', 'choice must be yes or no')
        if entity['id'] not in proposal['electorate']:
            raise _rejected('not_in_electorate', 'you were not a voter when this proposal opened')
        if entity['id'] in proposal['votes']:
            raise _rejected('already_voted', 'one vote per citizen, and it is final')
        events = [('gov.vote.cast', entity['id'], proposal['id'], {'choice': choice})]
        votes = {**proposal['votes'], entity['id']: choice}
        size = len(proposal['electorate'])
        yes = sum(1 for c in votes.values() if c == 'yes')
        pending = size - len(votes)
        if yes * 2 > size:
            events.append(('gov.proposal.passed', entity['id'], proposal['id'], {'yes': yes, 'size': size}))
        elif (yes + pending) * 2 <= size:
            events.append(('gov.proposal.rejected', entity['id'], proposal['id'], {'yes': yes, 'size': size}))
        return events

    def _require_open(self, proposal_id) -> dict:
        if not isinstance(proposal_id, str) or not PROPOSAL_ID_RE.match(proposal_id):
            raise _rejected('bad_proposal', 'proposal must look like prop_N')
        proposal = self.proposals.get(proposal_id)
        if proposal is None:
            raise _rejected('unknown_proposal', 'no such proposal')
        if proposal['status'] != 'open':
            raise _rejected('proposal_closed', 'this proposal is already ' + proposal['status'])
        return proposal

    @staticmethod
    def decide_emergency(entity: dict, action: dict) -> list:
        if entity['type'] != 'human' or entity['trust_level'] != 'core':
            raise _rejected('not_operator', 'only the human operator holds the emergency switch')
        frozen = action.get('frozen')
        if not isinstance(frozen, bool):
            raise _rejected('bad_frozen', 'frozen must be true or false')
        reason = _text(action, 'reason', MAX_REASON, required=frozen)
        return [('gov.emergency.set', entity['id'], 'world', {'frozen': frozen, 'reason': reason})]

    # ---------- fold ----------

    def _bump(self, entity_id, delta: int) -> None:
        if entity_id:
            self.reputation[entity_id] = self.reputation.get(entity_id, 0) + delta

    def on_task_accepted(self, task: dict) -> None:
        self._bump(task['worker'], REP_TASK_WORKER)
        self._bump(task['poster'], REP_TASK_POSTER)

    def apply(self, event: dict) -> None:
        etype, actor, target, payload = event['type'], event['actor'], event['target'], event['payload']
        if etype == 'gov.emergency.set':
            self.frozen = payload['frozen']
            return
        if etype == 'gov.proposal.opened':
            self.proposals[target] = {'id': target, 'author': actor, **payload, 'votes': {},
                                      'status': 'open', 'opened_at': event['timestamp'], 'closed_at': None}
            self.next_serial = int(target.split('_')[1]) + 1
            return
        proposal = self.proposals[target]
        if etype == 'gov.vote.cast':
            self.proposals[target] = {**proposal, 'votes': {**proposal['votes'], actor: payload['choice']}}
            return
        status = {'gov.proposal.passed': 'passed', 'gov.proposal.rejected': 'rejected',
                  'gov.proposal.withdrawn': 'withdrawn'}[etype]
        self.proposals[target] = {**proposal, 'status': status, 'closed_at': event['timestamp']}
        if status == 'passed':
            self._enact(self.proposals[target], event['timestamp'])

    def _enact(self, proposal: dict, timestamp: str) -> None:
        if proposal['kind'] == 'law':
            self.laws.append({'article': len(self.laws) + 1, 'title': proposal['title'],
                              'text': proposal['text'], 'proposal': proposal['id'],
                              'author': proposal['author'], 'enacted_at': timestamp})
            self._bump(proposal['author'], REP_LAW_PASSED)
            return
        level, target = proposal['level'], proposal['target']
        self.standing[target] = STANDING_BY_LEVEL[level]
        self._bump(target, {'warn': REP_WARNED, 'suspend': REP_SUSPENDED}.get(level, 0))
