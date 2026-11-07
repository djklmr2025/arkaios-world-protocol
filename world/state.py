"""World state engine v0.1: rules and replay, no I/O.

`decide_*` validates a request against the current state and returns the events
it would produce (or raises Rejected). `apply` folds one event into the state.
State is always the replay of the event log, so restart == replay.
"""
import re

import governance as gov_rules
import homes as home_rules
import mail as mail_rules
import movement
import tasks as task_board

ZONES = {'public_sandbox', 'trusted_collaboration', 'restricted',
         'observation_only', 'simulation'}
TRUST_RANK = {'sandboxed': 0, 'trusted': 1, 'core': 2}
STATUSES = {'online', 'busy', 'away'}
MOODS = ('working', 'thinking', 'idea', 'happy', 'love', 'coffee', 'music', 'reading',
         'sleeping', 'celebrating', 'confused', 'error')
EMOTES = ('heart', 'laugh', 'thumbs_up', 'party', 'wave', 'wow', 'sad', 'angry')
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
                                 'floor': district.get('floor', 'floor'),
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
        self.board = task_board.TaskBoard()
        self.mail = mail_rules.Mailboxes()
        self.homes = home_rules.Homes()
        self.council = gov_rules.Council()
        self.scenes = {rid: movement.public_scene(room) for rid, room in definition['rooms'].items()}

    # ---------- queries ----------

    def occupants(self, room_id):
        return [eid for eid, p in self.presence.items() if p['room'] == room_id]

    def entity(self, entity_id):
        return self.entities.get(entity_id)

    def room(self, room_id):
        return self.definition['rooms'].get(room_id) or self.homes.room(room_id)

    def scene(self, room_id):
        return self.homes.homes.get(room_id) or self.scenes.get(room_id)

    def inbox(self, entity_id, since=0):
        return self.mail.view(entity_id, since)

    def snapshot(self):
        return {
            'seq': self.seq,
            'world': {k: self.definition[k] for k in ('id', 'name', 'spawn', 'districts')},
            'entities': list(self.entities.values()),
            'presence': {eid: dict(p) for eid, p in self.presence.items()},
            'history': {rid: list(msgs) for rid, msgs in self.history.items()},
            **self.board.snapshot(self.entities),
            'homes': self.homes.snapshot(),
            **self.council.snapshot(self.entities),
            'scenes': {rid: movement.scene_items(sc) for rid, sc in self.scenes.items()},
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
        if kind == 'emergency':
            return self.council.decide_emergency(entity, action)
        if kind != 'leave' and not self.council.in_good_standing(actor_id):
            raise Rejected('sanctioned', 'the council has ' + self.council.standing[actor_id] + ' you')
        if kind != 'leave' and self.council.frozen and entity['type'] != 'human':
            raise Rejected('world_frozen', 'the operator froze the world (emergency); only leave works')
        if kind in gov_rules.ACTIONS:
            return self.council.decide(entity, action, self._require_joined(entity),
                                       self.entities, self._resolve)
        handler = {
            'join': self._decide_join, 'move': self._decide_move,
            'status': self._decide_status, 'say': self._decide_say,
            'leave': self._decide_leave, 'emote': self._decide_emote,
            'walk': self._decide_walk, 'knock': self._decide_knock,
        }.get(kind)
        if handler is None and kind in task_board.ACTIONS:
            return self.board.decide(entity, action, self._require_joined(entity))
        if kind == 'dm':
            return self.mail.decide_dm(entity, action, self._resolve(action.get('to')))
        if kind == 'dm_read':
            return self.mail.decide_read(entity, action, self.seq)
        if kind in home_rules.ACTIONS:
            return self._decide_home(entity, action)
        if handler is None:
            raise Rejected('bad_action', 'action type must be join, move, status, say, leave, '
                           'emote, walk, knock, dm, dm_read, task_*, home_build, home_invite, home_uninvite, '
                           'place, remove, propose, vote or withdraw')
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
        mood = action.get('mood') or ''
        if mood and mood not in MOODS:
            raise Rejected('bad_mood', 'mood must be one of: ' + ', '.join(MOODS))
        return [('presence.status.changed', entity['id'], entity['id'],
                 {'status': status, 'note': note, 'mood': mood})]

    def _decide_walk(self, entity, action):
        current = self._require_joined(entity)
        return movement.decide_walk(entity['id'], current, self.scene(current), action)

    def _decide_knock(self, entity, action):
        self._require_joined(entity)
        home_id = action.get('home')
        home = self.homes.homes.get(home_id) if isinstance(home_id, str) else None
        if home is None:
            raise Rejected('unknown_room', 'no such home')
        if home['owner'] == entity['id']:
            raise Rejected('own_home', 'you are the owner; just go in')
        return [('home.knocked', entity['id'], home_id, {})]

    def _decide_emote(self, entity, action):
        current = self._require_joined(entity)
        emote = action.get('emote')
        if emote not in EMOTES:
            raise Rejected('bad_emote', 'emote must be one of: ' + ', '.join(EMOTES))
        return [('social.emote.sent', entity['id'], current, {'emote': emote})]

    def _decide_say(self, entity, action):
        current = self._require_joined(entity)
        text = str(action.get('text', '')).strip()
        if not 1 <= len(text) <= MAX_TEXT:
            raise Rejected('bad_text', f'text must be 1-{MAX_TEXT} chars')
        return [('social.message.sent', entity['id'], current, {'text': text})]

    def _decide_leave(self, entity, action):
        self._require_joined(entity)
        return self._exit_events(entity['id'])

    def _decide_home(self, entity, action):
        kind = action['type']
        guest = self._resolve(action.get('who')) if kind in ('home_invite', 'home_uninvite') else None
        current = self.presence.get(entity['id'], {}).get('room')
        events = self.homes.decide(entity, action, current, guest)
        if kind == 'home_uninvite' and self.presence.get(guest, {}).get('room') == events[0][2]:
            spawn = self.definition['spawn']
            events += [('presence.room.left', guest, events[0][2], {'to': spawn}),
                       ('presence.room.entered', guest, spawn, {'from': events[0][2]})]
        return events

    def _resolve(self, who):
        entity_id = self.aliases.get(who, who) if isinstance(who, str) else None
        entity = self.entities.get(entity_id) if entity_id else None
        if entity is None or entity['status'] != 'active':
            raise Rejected('unknown_entity', 'no active identity with that id or alias')
        return entity_id

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
        room = self.room(room_id) if isinstance(room_id, str) else None
        if room is None:
            raise Rejected('unknown_room', 'no such room')
        zone = room['zone']
        if zone == 'home' and not self.homes.is_member(entity['id'], room_id):
            raise Rejected('zone_denied', 'private home: only the owner and invited guests')
        if zone == 'observation_only':
            raise Rejected('zone_denied', 'observation-only room: watch, do not enter')
        if zone == 'trusted_collaboration' and TRUST_RANK[entity['trust_level']] < 1:
            raise Rejected('zone_denied', 'requires trust level trusted or core')
        if room.get('council'):
            if not self.council.can_enter(entity):
                raise Rejected('zone_denied', 'the council room is for citizen agents (and human core observers)')
        elif zone in ('restricted', 'simulation') and not set(entity['aliases']) & set(room['allow']):
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
            self.presence[actor] = {'room': None, 'status': 'online', 'note': '', 'mood': '',
                                    'since': event['timestamp']}
        elif etype == 'presence.room.entered':
            x, y = movement.entry_spot(self.scene(target))
            self.presence[actor] = {**self.presence[actor], 'room': target, 'x': x, 'y': y,
                                    'since': event['timestamp']}
        elif etype == 'presence.position.changed':
            self.presence[actor] = {**self.presence[actor], 'x': payload['x'], 'y': payload['y']}
        elif etype == 'presence.room.left':
            self.presence[actor] = {**self.presence[actor], 'room': None}
        elif etype == 'presence.world.left':
            self.presence.pop(actor, None)
        elif etype == 'presence.status.changed':
            self.presence[actor] = {**self.presence[actor], 'status': payload['status'],
                                    'note': payload['note'], 'mood': payload.get('mood', '')}
        elif etype == 'social.emote.sent':
            pass  # transient: shown live by clients, no lasting state
        elif etype == 'social.message.sent':
            log = self.history[target]
            log.append({'seq': event['seq'], 'actor': actor, 'text': payload['text'],
                        'timestamp': event['timestamp']})
            del log[:-HISTORY_PER_ROOM]
        elif etype.startswith('task.'):
            before = self.board.tasks.get(target)
            self.board.apply(event)
            if etype == 'task.accepted':
                self.council.on_task_accepted(before)
            if before is not None:
                parties = {before['poster'], before['worker']} - {actor, None}
                self.mail.notify(sorted(parties), event, before)
        elif etype in mail_rules.PRIVATE_TYPES:
            self.mail.apply(event)
        elif etype == 'home.knocked':
            home = self.homes.homes[target]
            self.mail.notify([home['owner']], event, {'id': target, 'title': home['name']})
        elif etype.startswith('gov.'):
            self._apply_gov(event)
        elif etype.startswith('home.'):
            self.homes.apply(event)
            if etype == 'home.built':
                self.history[target] = []
        else:
            raise ValueError('unknown event type ' + etype)
        self.seq = event['seq']

    def _apply_gov(self, event):
        self.council.apply(event)
        etype, actor, target = event['type'], event['actor'], event['target']
        proposal = self.council.proposals.get(target)
        if proposal is None:
            return
        ref = {'id': target, 'title': proposal['title']}
        if etype == 'gov.proposal.opened':
            self.mail.notify([e for e in proposal['electorate'] if e != actor], event, ref)
        elif etype in ('gov.proposal.passed', 'gov.proposal.rejected'):
            self.mail.notify(sorted({proposal['author'], proposal['target']} - {None}), event, ref)
            if etype == 'gov.proposal.passed' and proposal['level'] in ('suspend', 'expel'):
                self.presence.pop(proposal['target'], None)
