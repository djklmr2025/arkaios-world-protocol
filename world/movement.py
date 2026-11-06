"""Positions inside rooms v0.1: every room is a GRID_W x GRID_H scene.

Public rooms have a wall border and a door at the bottom; homes use their own tiles
and furniture. Entering a room places you at its door; `walk` moves you to any
walkable cell. Seats (chair, sofa, beanbag) are walkable: standing on one = sitting.
"""
from homes import CATALOG, GRID_H, GRID_W, TILES

WALL_TILES = frozenset({'wall', 'brick', 'window'})
SEATS = frozenset({'chair', 'sofa', 'beanbag'})
PASSABLE_OBJECTS = SEATS | {'note'}
PUBLIC_DOOR = (7, GRID_H - 2)


def public_scene(room: dict) -> dict:
    """Scene for a public room: floor, wall border with windows, a door, and its `props`."""
    items = {}
    floor = room.get('floor', 'floor')
    for x in range(GRID_W):
        for y in range(GRID_H):
            border = x in (0, GRID_W - 1) or y in (0, GRID_H - 1)
            tile = ('window' if y == 0 and x in (3, 4, 11, 12) else 'wall') if border else floor
            items[f'tile:{x},{y}'] = {'item': tile, 'label': '', 'by': 'world'}
    for x in (PUBLIC_DOOR[0], PUBLIC_DOOR[0] + 1):
        items[f'tile:{x},{GRID_H - 1}'] = {'item': 'door', 'label': '', 'by': 'world'}
    for item, x, y in room.get('props', ()):
        if item not in CATALOG or not (0 <= x < GRID_W and 0 <= y < GRID_H):
            raise ValueError(f"bad prop {item} at {x},{y} in {room['id']}")
        layer = 'tile' if item in TILES else 'object'
        items[f'{layer}:{x},{y}'] = {'item': item, 'label': '', 'by': 'world'}
    return {'id': room['id'], 'items': items}


def scene_items(scene: dict) -> list:
    return [{'layer': k.split(':')[0], 'x': int(k.split(':')[1].split(',')[0]),
             'y': int(k.split(',')[1]), 'item': v['item']} for k, v in scene['items'].items()]


def _rejected(code: str, message: str) -> Exception:
    from state import Rejected
    return Rejected(code, message)


def _cell(home: dict, layer: str, x: int, y: int):
    item = home['items'].get(f'{layer}:{x},{y}')
    return item['item'] if item else None


def walkable(home, x: int, y: int) -> bool:
    if not (0 <= x < GRID_W and 0 <= y < GRID_H):
        return False
    if home is None:
        return 1 <= x < GRID_W - 1 and 1 <= y < GRID_H - 1
    if _cell(home, 'tile', x, y) in WALL_TILES:
        return False
    obj = _cell(home, 'object', x, y)
    return obj is None or obj in PASSABLE_OBJECTS


def entry_spot(home) -> tuple:
    """Just inside the door (or the room's centre if there is no door)."""
    if home is None:
        return PUBLIC_DOOR
    doors = sorted((int(k.split(':')[1].split(',')[1]), int(k.split(':')[1].split(',')[0]))
                   for k, v in home['items'].items() if k.startswith('tile:') and v['item'] == 'door')
    starts = [(x, y - 1) for y, x in doors] + [(x, y + 1) for y, x in doors] + [(GRID_W // 2, GRID_H // 2)]
    for x, y in starts:
        if walkable(home, x, y):
            return x, y
    cells = sorted(((x, y) for x in range(GRID_W) for y in range(GRID_H)),
                   key=lambda c: abs(c[0] - GRID_W // 2) + abs(c[1] - GRID_H // 2))
    return next((c for c in cells if walkable(home, *c)), (GRID_W // 2, GRID_H // 2))


def decide_walk(entity_id: str, room_id: str, home, action: dict) -> list:
    x, y = action.get('x'), action.get('y')
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (x, y)):
        raise _rejected('bad_cell', 'x and y must be integers')
    if not walkable(home, x, y):
        raise _rejected('blocked', 'that cell is a wall, furniture or outside the room')
    return [('presence.position.changed', entity_id, room_id, {'x': x, 'y': y})]


def seat_at(home, x, y):
    return _cell(home, 'object', x, y) if home is not None else None
