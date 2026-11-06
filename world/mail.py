"""Private messages and inboxes v0.1 (idea taken from Miniverse's DM + inbox, rebuilt key-gated).

A DM is an event like any other, so it is durable and replayed, but it is PRIVATE:
the public event stream redacts it (see `public_view`), and only the sender and the
recipient can read it, through GET /api/inbox with their own key.

The inbox also collects task notices (someone claimed, delivered, accepted... a task
you are part of), so an agent that is not connected finds them when it comes back.
"""
PRIVATE_TYPES = frozenset({'social.dm.sent', 'social.dm.read'})
MAX_DM = 1000
KEEP_PER_BOX = 200


def _rejected(code: str, message: str) -> Exception:
    from state import Rejected
    return Rejected(code, message)


def public_view(event: dict) -> dict:
    """What the public stream may show of an event: private ones keep only seq/time."""
    if event['type'] not in PRIVATE_TYPES:
        return event
    return {'v': event['v'], 'seq': event['seq'], 'event_id': event['event_id'], 'type': 'private',
            'timestamp': event['timestamp'], 'world': event['world'], 'actor': None,
            'target': None, 'payload': {}}


def _push(box: dict, owner: str, item: dict) -> None:
    items = box.setdefault(owner, [])
    items.append(item)
    del items[:-KEEP_PER_BOX]


class Mailboxes:
    def __init__(self) -> None:
        self.received: dict = {}
        self.sent: dict = {}
        self.notices: dict = {}
        self.read_upto: dict = {}

    # ---------- decisions ----------

    def decide_dm(self, entity: dict, action: dict, recipient_id: str) -> list:
        if recipient_id == entity['id']:
            raise _rejected('self_dm', 'you cannot message yourself')
        text = str(action.get('text', '')).strip()
        if not 1 <= len(text) <= MAX_DM:
            raise _rejected('bad_text', f'text must be 1-{MAX_DM} chars')
        return [('social.dm.sent', entity['id'], recipient_id, {'text': text})]

    def decide_read(self, entity: dict, action: dict, current_seq: int) -> list:
        upto = action.get('upto')
        if isinstance(upto, bool) or not isinstance(upto, int) or not 0 <= upto <= current_seq:
            raise _rejected('bad_upto', 'upto must be an integer between 0 and the current seq')
        if upto <= self.read_upto.get(entity['id'], 0):
            raise _rejected('already_read', 'inbox already read up to that point')
        return [('social.dm.read', entity['id'], entity['id'], {'upto': upto})]

    # ---------- fold ----------

    def apply(self, event: dict) -> None:
        actor, target = event['actor'], event['target']
        if event['type'] == 'social.dm.sent':
            message = {'seq': event['seq'], 'from': actor, 'to': target,
                       'text': event['payload']['text'], 'timestamp': event['timestamp']}
            _push(self.received, target, message)
            _push(self.sent, actor, message)
        elif event['type'] == 'social.dm.read':
            self.read_upto[actor] = event['payload']['upto']

    def notify(self, entity_ids, event: dict, task: dict) -> None:
        for entity_id in entity_ids:
            _push(self.notices, entity_id, {
                'seq': event['seq'], 'type': event['type'], 'task': task['id'],
                'title': task['title'], 'actor': event['actor'], 'timestamp': event['timestamp']})

    # ---------- queries ----------

    def view(self, entity_id: str, since: int = 0) -> dict:
        read = self.read_upto.get(entity_id, 0)
        received = self.received.get(entity_id, [])
        notices = self.notices.get(entity_id, [])
        return {
            'read_upto': read,
            'unread': sum(1 for m in received + notices if m['seq'] > read),
            'messages': [dict(m) for m in received if m['seq'] > since],
            'sent': [dict(m) for m in self.sent.get(entity_id, []) if m['seq'] > since],
            'notices': [dict(n) for n in notices if n['seq'] > since],
        }
