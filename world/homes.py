"""Homes v0.1: every identity can build one private home and furnish it cell by cell.

A home is a room of zone `home` (district `casas`) that only its owner and invited
guests can enter. Members place and remove catalog items on a GRID_W x GRID_H grid; each cell holds
one tile (floor, wall, door...) and one object on top (desk, plant...). Item art is
from Miniverse (MIT), see client/assets/LICENSE-miniverse.txt.
The interior is visible to everyone watching the world (like windows), entry is not.
"""
GRID_W = 16
GRID_H = 10
HOME_CAPACITY = 8
MAX_GUESTS = 8
MAX_ITEMS = GRID_W * GRID_H * 2
MAX_NAME = 40
MAX_LABEL = 60
DISTRICT = 'casas'
TILES = ('floor', 'wood', 'wall', 'brick', 'door', 'window', 'rug')
OBJECTS = ('desk', 'chair', 'computer', 'sofa', 'beanbag', 'table', 'lamp', 'plant', 'bookshelf',
           'shelf', 'art', 'coffee', 'fridge', 'cooler', 'whiteboard', 'speaker', 'note')
CATALOG = TILES + OBJECTS
LAYERS = ('tile', 'object')
ACTIONS = ('home_build', 'home_invite', 'home_uninvite', 'place', 'remove')


def _rejected(code: str, message: str) -> Exception:
    from state import Rejected
    return Rejected(code, message)


def home_id(entity_id: str) -> str:
    return f'room:{DISTRICT}:{entity_id.rsplit(":", 1)[1]}'


class Homes:
    def __init__(self) -> None:
        self.homes: dict = {}

    # ---------- queries ----------

    def room(self, room_id: str):
        home = self.homes.get(room_id)
        if home is None:
            return None
        return {'id': room_id, 'name': home['name'], 'zone': 'home', 'district': DISTRICT,
                'capacity': HOME_CAPACITY, 'allow': ()}

    def is_member(self, entity_id: str, room_id: str) -> bool:
        home = self.homes.get(room_id)
        return bool(home) and (entity_id == home['owner'] or entity_id in home['guests'])

    def snapshot(self) -> list:
        return [{**h, 'guests': list(h['guests']),
                 'items': [{'layer': k.split(':')[0], 'x': int(k.split(':')[1].split(',')[0]),
                            'y': int(k.split(',')[1]), **v} for k, v in h['items'].items()]}
                for h in self.homes.values()]

    # ---------- decisions ----------

    def decide(self, entity: dict, action: dict, current_room, guest_id=None) -> list:
        kind, actor = action['type'], entity['id']
        if kind == 'home_build':
            room_id = home_id(actor)
            if room_id in self.homes:
                raise _rejected('home_exists', 'you already have a home')
            name = str(action.get('name') or f"Casa de {entity['display_name']}").strip()[:MAX_NAME]
            return [('home.built', actor, room_id, {'name': name})]
        if kind in ('home_invite', 'home_uninvite'):
            home = self.homes.get(home_id(actor))
            if home is None:
                raise _rejected('no_home', 'build your home first')
            if guest_id == actor:
                raise _rejected('bad_guest', 'you already own this home')
            if kind == 'home_invite':
                if guest_id in home['guests']:
                    raise _rejected('already_guest', 'already invited')
                if len(home['guests']) >= MAX_GUESTS:
                    raise _rejected('too_many_guests', f'at most {MAX_GUESTS} guests')
                return [('home.member.added', actor, home['id'], {'guest': guest_id})]
            if guest_id not in home['guests']:
                raise _rejected('not_guest', 'that identity is not a guest')
            return [('home.member.removed', actor, home['id'], {'guest': guest_id})]
        if current_room is None or current_room not in self.homes:
            raise _rejected('not_home', 'go inside a home to build')
        if not self.is_member(actor, current_room):
            raise _rejected('not_member', 'only the owner and guests can build here')
        home = self.homes[current_room]
        x, y = self._cell(action)
        if kind == 'place':
            item = action.get('item')
            if item not in CATALOG:
                raise _rejected('bad_item', 'item must be one of: ' + ', '.join(CATALOG))
            layer = 'tile' if item in TILES else 'object'
            if f'{layer}:{x},{y}' in home['items']:
                raise _rejected('cell_taken', 'that cell already has something')
            if len(home['items']) >= MAX_ITEMS:
                raise _rejected('home_full', f'at most {MAX_ITEMS} items per home')
            label = str(action.get('label', '')).strip()[:MAX_LABEL]
            return [('home.item.placed', actor, current_room,
                     {'item': item, 'layer': layer, 'x': x, 'y': y, 'label': label})]
        layer = action.get('layer')
        if layer is None:
            layer = 'object' if f'object:{x},{y}' in home['items'] else 'tile'
        if layer not in LAYERS:
            raise _rejected('bad_layer', 'layer must be tile or object')
        if f'{layer}:{x},{y}' not in home['items']:
            raise _rejected('cell_empty', 'nothing to remove there')
        return [('home.item.removed', actor, current_room, {'layer': layer, 'x': x, 'y': y})]

    @staticmethod
    def _cell(action: dict) -> tuple:
        x, y = action.get('x'), action.get('y')
        for v, limit in ((x, GRID_W), (y, GRID_H)):
            if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v < limit:
                raise _rejected('bad_cell', f'x must be 0-{GRID_W - 1} and y 0-{GRID_H - 1}')
        return x, y

    # ---------- fold ----------

    def apply(self, event: dict) -> None:
        etype, actor, room_id, payload = (event['type'], event['actor'], event['target'],
                                          event['payload'])
        if etype == 'home.built':
            self.homes[room_id] = {'id': room_id, 'name': payload['name'], 'owner': actor,
                                   'guests': (), 'items': {}, 'built_at': event['timestamp']}
            return
        home = self.homes[room_id]
        if etype == 'home.member.added':
            home = {**home, 'guests': home['guests'] + (payload['guest'],)}
        elif etype == 'home.member.removed':
            home = {**home, 'guests': tuple(g for g in home['guests'] if g != payload['guest'])}
        elif etype == 'home.item.placed':
            items = {**home['items'], f"{payload['layer']}:{payload['x']},{payload['y']}":
                     {'item': payload['item'], 'label': payload['label'], 'by': actor}}
            home = {**home, 'items': items}
        elif etype == 'home.item.removed':
            key = f"{payload['layer']}:{payload['x']},{payload['y']}"
            home = {**home, 'items': {k: v for k, v in home['items'].items() if k != key}}
        else:
            raise ValueError('unknown event type ' + etype)
        self.homes[room_id] = home
