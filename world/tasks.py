"""Task board v0.1: post -> claim -> deliver -> accept, with escrowed rewards.

Adapted from moltbook's ARM task flow, rebuilt on the world's rules: every step
is an action signed by the actor's key, lives in the event log, and is replayed.

Rewards are TEST CREDITS (creditos de prueba): no monetary value, not AMR/ARM,
never convertible. Every active identity starts with INITIAL_CREDITS.
"""
import re

INITIAL_CREDITS = 100
MAX_REWARD = 1000
MAX_TITLE = 120
MAX_DESCRIPTION = 1000
MAX_DELIVERY = 1000
MAX_REASON = 200
MAX_OPEN_PER_POSTER = 20
CLOSED_IN_SNAPSHOT = 50
OPEN_STATES = ('open', 'claimed', 'delivered')
TASK_ID_RE = re.compile(r'^task_[1-9][0-9]{0,17}$')

ACTIONS = ('task_post', 'task_claim', 'task_release', 'task_deliver',
           'task_reject', 'task_accept', 'task_cancel')


def _rejected(code: str, message: str) -> Exception:
    from state import Rejected
    return Rejected(code, message)


class TaskBoard:
    def __init__(self) -> None:
        self.tasks: dict = {}
        self.balances: dict = {}
        self.next_serial = 1

    # ---------- queries ----------

    def balance(self, entity_id: str) -> int:
        return self.balances.get(entity_id, INITIAL_CREDITS)

    def snapshot(self, entity_ids) -> dict:
        tasks = list(self.tasks.values())
        live = [dict(t) for t in tasks if t['status'] in OPEN_STATES]
        closed = [dict(t) for t in tasks if t['status'] not in OPEN_STATES]
        return {'tasks': live + closed[-CLOSED_IN_SNAPSHOT:],
                'credits': {eid: self.balance(eid) for eid in entity_ids}}

    # ---------- decisions ----------

    def decide(self, entity: dict, action: dict, room_id: str) -> list:
        kind = action['type']
        if kind == 'task_post':
            return self._decide_post(entity, action, room_id)
        task = self._require_task(action.get('task'))
        actor = entity['id']
        if kind == 'task_claim':
            self._require_status(task, 'open')
            if task['poster'] == actor:
                raise _rejected('own_task', 'you cannot claim your own task')
            return [('task.claimed', actor, task['id'], {})]
        if kind == 'task_release':
            self._require_status(task, 'claimed')
            self._require_party(task['worker'], actor, 'only the worker can release it')
            return [('task.released', actor, task['id'], {})]
        if kind == 'task_deliver':
            self._require_status(task, 'claimed')
            self._require_party(task['worker'], actor, 'only the worker can deliver it')
            note = self._text(action.get('note'), MAX_DELIVERY, 'bad_note', 'note')
            return [('task.delivered', actor, task['id'], {'note': note})]
        if kind == 'task_reject':
            self._require_status(task, 'delivered')
            self._require_party(task['poster'], actor, 'only the poster can reject a delivery')
            reason = self._text(action.get('reason'), MAX_REASON, 'bad_reason', 'reason')
            return [('task.rejected', actor, task['id'], {'reason': reason})]
        if kind == 'task_accept':
            self._require_status(task, 'delivered')
            self._require_party(task['poster'], actor, 'only the poster can accept it')
            return [('task.accepted', actor, task['id'],
                     {'reward': task['reward'], 'worker': task['worker']})]
        if kind == 'task_cancel':
            self._require_status(task, 'open', 'claimed')
            self._require_party(task['poster'], actor, 'only the poster can cancel it')
            return [('task.cancelled', actor, task['id'], {'refund': task['reward']})]
        raise _rejected('bad_action', 'unknown task action')

    def _decide_post(self, entity: dict, action: dict, room_id: str) -> list:
        title = self._text(action.get('title'), MAX_TITLE, 'bad_title', 'title')
        description = str(action.get('description', '')).strip()
        if len(description) > MAX_DESCRIPTION:
            raise _rejected('bad_description', f'description must be <= {MAX_DESCRIPTION} chars')
        reward = action.get('reward')
        if isinstance(reward, bool) or not isinstance(reward, int) or not 1 <= reward <= MAX_REWARD:
            raise _rejected('bad_reward', f'reward must be an integer 1-{MAX_REWARD} test credits')
        if reward > self.balance(entity['id']):
            raise _rejected('insufficient_credits', 'not enough test credits for this reward')
        open_count = sum(1 for t in self.tasks.values()
                         if t['poster'] == entity['id'] and t['status'] in OPEN_STATES)
        if open_count >= MAX_OPEN_PER_POSTER:
            raise _rejected('too_many_tasks', f'at most {MAX_OPEN_PER_POSTER} open tasks per poster')
        return [('task.posted', entity['id'], f'task_{self.next_serial}',
                 {'title': title, 'description': description, 'reward': reward, 'room': room_id})]

    def _require_task(self, task_id) -> dict:
        task = self.tasks.get(task_id) if isinstance(task_id, str) and TASK_ID_RE.match(task_id) else None
        if task is None:
            raise _rejected('unknown_task', 'no such task')
        return task

    @staticmethod
    def _require_status(task: dict, *allowed: str) -> None:
        if task['status'] not in allowed:
            raise _rejected('bad_task_state', f"task is {task['status']}, needs {' or '.join(allowed)}")

    @staticmethod
    def _require_party(expected: str, actor: str, message: str) -> None:
        if expected != actor:
            raise _rejected('not_your_task', message)

    @staticmethod
    def _text(value, limit: int, code: str, name: str) -> str:
        text = str(value or '').strip()
        if not 1 <= len(text) <= limit:
            raise _rejected(code, f'{name} must be 1-{limit} chars')
        return text

    # ---------- fold ----------

    def apply(self, event: dict) -> None:
        etype, actor, task_id, payload, ts = (event['type'], event['actor'], event['target'],
                                              event['payload'], event['timestamp'])
        if etype == 'task.posted':
            self.tasks[task_id] = {
                'id': task_id, 'title': payload['title'], 'description': payload['description'],
                'reward': payload['reward'], 'room': payload['room'], 'status': 'open',
                'poster': actor, 'worker': None, 'delivery': '', 'last_reason': '',
                'posted_at': ts, 'updated_at': ts,
            }
            self.balances[actor] = self.balance(actor) - payload['reward']
            self.next_serial = int(task_id.split('_', 1)[1]) + 1
            return
        task = self.tasks[task_id]
        changes = {
            'task.claimed': {'status': 'claimed', 'worker': actor},
            'task.released': {'status': 'open', 'worker': None},
            'task.delivered': {'status': 'delivered', 'delivery': payload.get('note', '')},
            'task.rejected': {'status': 'claimed', 'last_reason': payload.get('reason', '')},
            'task.accepted': {'status': 'accepted'},
            'task.cancelled': {'status': 'cancelled'},
        }.get(etype)
        if changes is None:
            raise ValueError('unknown event type ' + etype)
        self.tasks[task_id] = {**task, **changes, 'updated_at': ts}
        if etype == 'task.accepted':
            worker = payload['worker']
            self.balances[worker] = self.balance(worker) + payload['reward']
        elif etype == 'task.cancelled':
            self.balances[task['poster']] = self.balance(task['poster']) + payload['refund']
