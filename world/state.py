"""World state engine v0.1: rules and replay, no I/O.

`decide_*` validates a request against the current state and returns the events
it would produce (or raises Rejected). `apply` folds one event into the state.
State is always the replay of the event log, so restart == replay.
"""
import re

ZONES = {'public_sandbox', 'trusted_collaboration', 'restricted',
         'observation_only', 'simulation'}
TRUST_RANK = {'sandboxed': 0, 'trusted': 1, 'core': 2}
STATUSES = {'online', 'busy', 'away'}
ENTITY_TYPES = {'agent', 'human'}
MAX_TEXT = 500
MAX_NOTE = 80
HISTORY_PER_ROOM = 30
ALIAS_RE = re.compile(r'^[a-z0-9][a-z0-9_-]{0,31}$')
CAPABILITY_RE = re.compile(r'^[a-z0-9_]{1,40}$')
REGISTRY_RE = re.compile(r'^[a-z0-9-]{1,40}$')


class Rejected(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def load_world_definition(raw):
    rooms = {}
    for district in raw['districts']:
        for room in district['rooms']:
            if room['id'] in rooms:
                raise ValueError('duplicate room ' + room['id'])
            if room['zone'] not in ZONES:
                raise ValueError('unknown zone ' + room['zone'])
            rooms[room['id']] = {**room, 'district': district['id'],
                                 'allow': tuple(room.get('allow', ()))}
    if raw['spawn'] not in rooms or rooms[raw['spawn']]['zone'] != 'public_sandbox':
        raise ValueError('spawn must be an existing public_sandbox room')
    return {'id': raw['id'], 'name': raw['name'], 'spawn': raw['spawn'],
            'districts': raw['districts'], 'rooms': rooms}


class WorldState:
    def __init__(self, definition, registry_id='local-alpha'):
        if not REGISTRY_RE.match(registry_id):
            raise ValueError('invalid registry id')
        self.definition = definition
        self.registry_id = registry_id
        self.seq = 0
        self.entities = {}
        self.aliases = {}
        self.presence = {}
        self.history = {room_id: [] for room_id in definition['rooms']}
        self.next_serial = 1

    # ---------- queries ----------

    def occupants(self, room_id):
        return [eid for eid, p in self.presence.items() if p['room'] == room_id]

    def entity(self, entity_id):
        return self.entities.get(entity_id)

    def snapshot(self):
        return {
            'seq': self.seq,
            'world': {k: self.definition[k] for k in ('id', 'name', 'spawn', 'districts')},
            'entities': list(self.entities.values()),
            'presence': {eid: dict(p) for eid, p in self.presence.items()},
            'history': {rid: list(msgs) for rid, msgs in self.history.items()},
        }

    # ---------- registry decisions (human operator only) ----------

    def decide_register(self, spec, now):
        etype = spec.get('type')
        name = str(spec.get('display_name', '')).strip()
        owner = str(spec.get('owner', '')).strip()
        trust = spec.get('trust_level', 'sandboxed')
        aliases = list(dict.fromkeys(spec.get('aliases', [])))
        capabilities = list(dict.fromkeys(spec.get('capabilities', [])))
        if etype not in ENTITY_TYPES:
            raise Rejected('bad_type', 'type must be agent or human')
        if not 1 <= len(name) <= 40:
            raise Rejected('bad_name', 'display_name must be 1-40 chars')
        if not 1 <= len(owner) <= 80:
            raise Rejected('bad_owner', 'owner must be 1-80 chars')
        if trust not in TRUST_RANK:
            raise Rejected('bad_trust', 'trust_level must be sandboxed, trusted or core')
        if len(aliases) > 8 or not all(ALIAS_RE.match(a) for a in aliases):
            raise Rejected('bad_alias', 'aliases: up to 8, lowercase [a-z0-9_-]')
        taken = [a for a in aliases if a in self.aliases]
        if taken:
            raise Rejected('alias_taken', 'alias already registered: ' + ', '.join(taken))
        if len(capabilities) > 16 or not all(CAPABILITY_RE.match(c) for c in capabilities):
            raise Rejected('bad_capability', 'capabilities: up to 16, [a-z0-9_]')
        identity = {
            'id': f'ark:{self.registry_id}:{self.next_serial}',
            'type': etype, 'display_name': name, 'aliases': aliases, 'owner': owner,
            'provider': str(spec.get('provider', ''))[:40],
            'capabilities': capabilities, 'trust_level': trust,
            'memory_ref': str(spec.get('memory_ref', ''))[:200],
            'status': 'active', 'created_at': now,
        }
        return [('identity.registered', 'registry', identity['id'], identity)]

    def decide_revoke(self, entity_id, reason):
        entity = self.entities.get(entity_id)
        if entity is None:
            raise Rejected('unknown_entity', 'no such entity')
        if entity['status'] == 'revoked':
            raise Rejected('already_revoked', 'entity already revoked')
        events = self._exit_events(entity_id)
        events.append(('identity.revoked', 'registry', entity_id,
                       {'reason': str(reason)[:200]}))
        return events

    # ---------- entity actions ----------

    def decide_action(self, actor_id, action):
        entity = self.entities.get(actor_id)
        if entity is None or entity['status'] != 'active':
            raise Rejected('inactive', 'entity is not active')
        kind = action.get('type')
        handler = {
            'join': self._decide_join, 'move': self._decide_move,
            'status': self._decide_status, 'say': self._decide_say,
            'leave': self._decide_leave,
        }.get(kind)
        if handler is None:
            raise Rejected('bad_action', 'action type must be join, move, status, say or leave')
        return handler(entity, action)

    def _decide_join(self, entity, action):
        if entity['id'] in self.presence:
            raise Rejected('already_joined', 'already in the world')
        room_id = action.get('room') or self.definition['spawn']
        self._check_entry(entity, room_id)
        world = self.definition['id']
        return [('presence.world.joined', entity['id'], world, {}),
                ('presence.room.entered', entity['id'], room_id, {'from': None})]

    def _decide_move(self, entity, action):
        current = self._require_joined(entity)
        room_id = action.get('room')
        if room_id == current:
            raise Rejected('same_room', 'already in that room')
        self._check_entry(entity, room_id)
        return [('presence.room.left', entity['id'], current, {'to': room_id}),
                ('presence.room.entered', entity['id'], room_id, {'from': current})]

    def _decide_status(self, entity, action):
        self._require_joined(entity)
        status = action.get('status')
        if status not in STATUSES:
            raise Rejected('bad_status', 'status must be online, busy or away')
        note = str(action.get('note', '')).strip()[:MAX_NOTE]
        return [('presence.status.changed', entity['id'], entity['id'],
                 {'status': status, 'note': note})]

    def _decide_say(self, entity, action):
        current = self._require_joined(entity)
        text = str(action.get('text', '')).strip()
        if not 1 <= len(text) <= MAX_TEXT:
            raise Rejected('bad_text', f'text must be 1-{MAX_TEXT} chars')
        return [('social.message.sent', entity['id'], current, {'text': text})]

    def _decide_leave(self, entity, action):
        self._require_joined(entity)
        return self._exit_events(entity['id'])

    def _require_joined(self, entity):
        presence = self.presence.get(entity['id'])
        if presence is None:
            raise Rejected('not_joined', 'join the world first')
        return presence['room']

    def _exit_events(self, entity_id):
        presence = self.presence.get(entity_id)
        if presence is None:
            return []
        return [('presence.room.left', entity_id, presence['room'], {'to': None}),
                ('presence.world.left', entity_id, self.definition['id'], {})]

    def _check_entry(self, entity, room_id):
        room = self.definition['rooms'].get(room_id)
        if room is None:
            raise Rejected('unknown_room', 'no such room')
        zone = room['zone']
        if zone == 'observation_only':
            raise Rejected('zone_denied', 'observation-only room: watch, do not enter')
        if zone == 'trusted_collaboration' and TRUST_RANK[entity['trust_level']] < 1:
            raise Rejected('zone_denied', 'requires trust level trusted or core')
        if zone in ('restricted', 'simulation') and not set(entity['aliases']) & set(room['allow']):
            raise Rejected('zone_denied', 'not on this room\'s allow list')
        if len(self.occupants(room_id)) >= room['capacity']:
            raise Rejected('room_full', 'room is at capacity')

    # ---------- fold ----------

    def apply(self, event):
        if event['seq'] != self.seq + 1:
            raise ValueError(f"event seq {event['seq']} after {self.seq}: log has a gap")
        etype, actor, target, payload = (event['type'], event['actor'],
                                         event['target'], event['payload'])
        if etype == 'identity.registered':
            self.entities[target] = dict(payload)
            for alias in payload['aliases']:
                self.aliases[alias] = target
            self.next_serial = int(target.rsplit(':', 1)[1]) + 1
        elif etype == 'identity.revoked':
            self.entities[target] = {**self.entities[target], 'status': 'revoked'}
        elif etype == 'presence.world.joined':
            self.presence[actor] = {'room': None, 'status': 'online', 'note': '',
                                    'since': event['timestamp']}
        elif etype == 'presence.room.entered':
            self.presence[actor] = {**self.presence[actor], 'room': target,
                                    'since': event['timestamp']}
        elif etype == 'presence.room.left':
            self.presence[actor] = {**self.presence[actor], 'room': None}
        elif etype == 'presence.world.left':
            self.presence.pop(actor, None)
        elif etype == 'presence.status.changed':
            self.presence[actor] = {**self.presence[actor], 'status': payload['status'],
                                    'note': payload['note']}
        elif etype == 'social.message.sent':
            log = self.history[target]
            log.append({'seq': event['seq'], 'actor': actor, 'text': payload['text'],
                        'timestamp': event['timestamp']})
            del log[:-HISTORY_PER_ROOM]
        else:
            raise ValueError('unknown event type ' + etype)
        self.seq = event['seq']
