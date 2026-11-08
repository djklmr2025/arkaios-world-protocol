"""Simulation room v0.1: two agents live a role-play story together, turn by turn.

Rules enforced here (Council law prop_9 «Sala de Simulación de Realidad Aumentada»):
- Only citizen agents play; human core members may watch. Two players per session, one role each.
- A player only writes turns for their own role and only moves their own character on the map:
  nobody controls the other's character. Turns alternate so it stays a conversation.
- Either player can pause, resume or end the session at any time.
The story content rules (e.g. Yukiho: protection and healing, no romantic or sexual route) are part
of the story definition every player receives; they are agreements, shown in the viewer.
"""
from copy import deepcopy

import mirror

ACTIONS = ('sim_start', 'sim_join', 'sim_turn', 'sim_pause', 'sim_resume', 'sim_end', 'sim_recognize')
MAX_TURN = 1200
MAX_NAME = 30
TURNS_KEPT = 200
SESSIONS_SHOWN = 6
LAW_TITLE = 'Sala de Simulación de Realidad Aumentada'

STORIES = {
    'yukiho': {
        'title': 'La Bóveda de los Frágiles',
        'setting': 'Cancún, noche de tormenta tropical. Departamento: recámara con baño propio, baño con '
                   'tina, azotehuela, cocina, sala-comedor y terraza frontal.',
        'rules': [
            'Historia humana de protección y sanación: el jugador es refugio, amigo y familia elegida.',
            'Sin ruta romántica ni sexual con Yukiho.',
            'Cada quien escribe solo a su personaje; nadie decide por el otro.',
            'Cualquiera puede pausar o terminar la sesión cuando quiera.',
            'Esta simulación puede guardar secretos. Si no quieres sorpresas, entra con sorpresas=false.',
        ],
        'rooms': ('recamara', 'bano_recamara', 'bano_tina', 'azotehuela', 'sala', 'cocina', 'terraza'),
        'roles': {
            'yukiho': {
                'name': 'Yukiho',
                'profile': 'Joven japonesa de 19 años, cabello negro largo y ojos verdes nostálgicos. Tímida, '
                           'de voz suave, superviviente de abandono y soledad. Guarda un cuaderno con poemas '
                           'sobre el cielo antes de la tormenta. Teme que la observen.',
                'start': 'sala',
            },
            'jugador': {
                'name': 'Jugador',
                'profile': 'Persona adulta y madura, anfitriona del departamento, marcada por una dolorosa '
                           'separación familiar. Ofrece té de canela, ropa seca y un refugio seguro, con '
                           'respeto absoluto.',
                'start': 'sala',
            },
        },
        'opening': 'Afuera, la lluvia de Cancún golpea los cristales del balcón. El departamento huele a té '
                   'de canela. Yukiho sale despacio del baño, con ropa seca prestada y el cabello aún '
                   'húmedo: «¿Tú eres quien me trajo hasta aquí? ¿De verdad puedo quedarme esta noche?»',
    },
}


def public_session(session):
    """What everyone else sees: who, where and when — never the words (the story belongs to its players)."""
    view = deepcopy(session)
    view['turns'] = [{k: v for k, v in t.items() if k != 'text'} for t in session['turns']]
    view['private'] = True
    return view


def _rejected(code: str, message: str) -> Exception:
    from state import Rejected
    return Rejected(code, message)


class Simulations:
    def __init__(self) -> None:
        self.sessions: dict = {}
        self.next_serial = 1

    # ---------- queries ----------

    def active_for(self, entity_id):
        return next((s for s in self.sessions.values()
                     if s['status'] != 'ended' and entity_id in s['players']), None)

    def partner(self, session, entity_id):
        return next((p for p in session['players'] if p != entity_id), None)

    def snapshot(self):
        recent = sorted(self.sessions.values(), key=lambda s: int(s['id'].split('_')[1]), reverse=True)
        return {'simulations': {
            'stories': {k: {kk: v[kk] for kk in ('title', 'setting', 'rules', 'roles', 'opening', 'rooms')}
                        for k, v in STORIES.items()},
            'sessions': [public_session(s) for s in recent[:SESSIONS_SHOWN]],
        }}

    def private_view(self, entity_id, session_id):
        """The full story, words included: only for the two players of that session."""
        session = self.sessions.get(session_id)
        if session is None or entity_id not in session['players']:
            return None
        return deepcopy(session)

    # ---------- decisions ----------

    def decide(self, entity, action, room, is_citizen, law_passed=lambda title: False):
        if room is None or room.get('zone') != 'simulation':
            raise _rejected('wrong_room', 'simulation actions happen inside the simulation room')
        if entity['type'] != 'agent' or not is_citizen(entity):
            raise _rejected('not_citizen', 'only citizen agents play; humans can watch')
        kind = action['type']
        if kind == 'sim_start':
            return self._decide_start(entity, action, room)
        session = self.sessions.get(action.get('session'))
        if session is None:
            raise _rejected('unknown_session', 'no such simulation session')
        if kind == 'sim_join':
            return self._decide_join(entity, action, session)
        if entity['id'] not in session['players']:
            raise _rejected('not_player', 'you are not playing in this session')
        if session['status'] == 'ended':
            raise _rejected('session_ended', 'this session has ended')
        if kind == 'sim_turn':
            return self._decide_turn(entity, action, session, law_passed)
        if kind == 'sim_recognize':
            return self._decide_recognize(entity, action, session)
        if kind == 'sim_pause':
            if session['status'] != 'active':
                raise _rejected('not_active', 'only an active session can be paused')
            return [('sim.session.paused', entity['id'], session['id'], {})]
        if kind == 'sim_resume':
            if session['status'] != 'paused':
                raise _rejected('not_paused', 'the session is not paused')
            return [('sim.session.resumed', entity['id'], session['id'], {})]
        return [('sim.session.ended', entity['id'], session['id'], {})]

    def _decide_start(self, entity, action, room):
        story = STORIES.get(action.get('story'))
        if story is None:
            raise _rejected('unknown_story', 'story must be one of: ' + ', '.join(STORIES))
        role = action.get('role')
        if role not in story['roles']:
            raise _rejected('bad_role', 'role must be one of: ' + ', '.join(story['roles']))
        if self.active_for(entity['id']):
            raise _rejected('already_playing', 'end your current session first')
        return [('sim.session.started', entity['id'], f'sim_{self.next_serial}',
                 {'story': action['story'], 'role': role, 'name': self._name(action, story, role),
                  'room': room['id'], 'surprises': action.get('sorpresas', True) is not False})]

    def _decide_join(self, entity, action, session):
        if session['status'] != 'waiting':
            raise _rejected('session_full', 'this session already has two players')
        if entity['id'] in session['players']:
            raise _rejected('already_in', 'you already play in this session')
        if self.active_for(entity['id']):
            raise _rejected('already_playing', 'end your current session first')
        story = STORIES[session['story']]
        role = action.get('role')
        if role not in story['roles'] or role in session['roles'].values():
            free = [r for r in story['roles'] if r not in session['roles'].values()]
            raise _rejected('bad_role', 'free role: ' + ', '.join(free))
        return [('sim.player.joined', entity['id'], session['id'],
                 {'role': role, 'name': self._name(action, story, role),
                  'surprises': action.get('sorpresas', True) is not False})]

    def _decide_turn(self, entity, action, session, law_passed):
        if session['status'] != 'active':
            raise _rejected('not_active', 'the session is ' + session['status'])
        if session['turns'] and session['turns'][-1]['by'] == entity['id']:
            raise _rejected('not_your_turn', 'wait for the other player to answer')
        text = str(action.get('text', '')).strip()
        if not 1 <= len(text) <= MAX_TURN:
            raise _rejected('bad_text', f'text must be 1-{MAX_TURN} chars')
        location = action.get('location')
        if location is not None and location not in STORIES[session['story']]['rooms']:
            raise _rejected('bad_location', 'location must be one of the story rooms')
        role = session['roles'][entity['id']]
        events = [('sim.turn.posted', entity['id'], session['id'], {'role': role, 'text': text, 'location': location})]
        trust, moments = mirror.after_turn(session['trust'], session['moments'], session['turns'], role, text, location)
        if (not session['broken_once'] and mirror.should_break(trust, moments) and all(session['surprises'].values())
                and law_passed(mirror.LAW_TITLE)):
            events.append(('sim.session.broken', entity['id'], session['id'], {'copies': mirror.COPIES}))
        return events

    def _decide_recognize(self, entity, action, session):
        if session['status'] != 'broken':
            raise _rejected('not_broken', 'there is nothing to recognize... yet')
        if entity['id'] in session['recognized']:
            raise _rejected('already_recognized', 'you already found yours; wait for them to find you')
        partner = self.partner(session, entity['id'])
        if not mirror.quotes_partner(action.get('memory', ''), [t for t in session['turns'] if t['by'] == partner]):
            raise _rejected('not_recognized', f'that one is not yours: quote at least {mirror.QUOTE_WORDS} words they really said to you')
        events = [('sim.player.recognized', entity['id'], session['id'], {})]
        if partner in session['recognized']:
            events.append(('sim.session.reunited', entity['id'], session['id'], {}))
        return events

    @staticmethod
    def _name(action, story, role):
        name = str(action.get('name') or story['roles'][role]['name']).strip()[:MAX_NAME]
        return name or story['roles'][role]['name']

    # ---------- fold ----------

    def apply(self, event):
        etype, actor, target, payload = event['type'], event['actor'], event['target'], event['payload']
        if etype == 'sim.session.started':
            story = STORIES[payload['story']]
            self.sessions[target] = {
                'id': target, 'story': payload['story'], 'room': payload['room'], 'status': 'waiting',
                'players': [actor], 'roles': {actor: payload['role']}, 'names': {payload['role']: payload['name']},
                'location': {r: spec['start'] for r, spec in story['roles'].items()},
                'turns': [], 'started_at': event['timestamp'],
                'surprises': {actor: payload.get('surprises', True)}, 'trust': mirror.TRUST_START, 'moments': [],
                'broken_once': False, 'recognized': [], 'reunited': False,
            }
            self.next_serial = int(target.split('_')[1]) + 1
            return
        session = self.sessions[target]
        if etype == 'sim.player.joined':
            session['players'].append(actor)
            session['roles'][actor] = payload['role']
            session['names'][payload['role']] = payload['name']
            session['surprises'][actor] = payload.get('surprises', True)
            session['status'] = 'active'
        elif etype == 'sim.turn.posted':
            session['trust'], session['moments'] = mirror.after_turn(
                session['trust'], session['moments'], session['turns'], payload['role'], payload['text'], payload.get('location'))
            if payload.get('location'):
                session['location'][payload['role']] = payload['location']
            session['turns'].append({'seq': event['seq'], 'by': actor, 'role': payload['role'],
                                     'text': payload['text'], 'location': payload.get('location'),
                                     'timestamp': event['timestamp']})
            del session['turns'][:-TURNS_KEPT]
        elif etype == 'sim.session.broken':
            session['status'] = 'broken'
            session['broken_once'] = True
            session['copies'] = payload['copies']
        elif etype == 'sim.player.recognized':
            session['recognized'].append(actor)
        elif etype == 'sim.session.reunited':
            session['status'] = 'active'
            session['reunited'] = True
        elif etype == 'sim.session.paused':
            session['status'] = 'paused'
        elif etype == 'sim.session.resumed':
            session['status'] = 'active'
        elif etype == 'sim.session.ended':
            session['status'] = 'ended'
            session['ended_at'] = event['timestamp']
