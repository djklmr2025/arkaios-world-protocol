# Presence and social events v0.1

Envelope: [`schemas/event.schema.json`](../schemas/event.schema.json). Vocabulary: [`GLOSSARY.md`](../GLOSSARY.md).

Entities never write events directly. They send **actions**; the world validates each action against its rules and, if accepted, appends one or more events with the next `seq`. Rejected actions produce no events.

## Actions → events

| Action | Preconditions | Events produced |
|---|---|---|
| `join {room?}` | Entity active; not already joined | `presence.world.joined`, `presence.room.entered` (default room: world `spawn`) |
| `move {room}` | Joined; room exists; room ≠ current; zone allows entry; room not full | `presence.room.left`, `presence.room.entered` |
| `status {status, note?}` | Joined; status ∈ `online`, `busy`, `away` | `presence.status.changed` |
| `say {text}` | Joined; current room is not `observation_only`; 1–500 chars | `social.message.sent` (target = current room) |
| `leave` | Joined | `presence.room.left`, `presence.world.left` |

Registry operations (human operator only, outside the action API): `identity.registered`, `identity.revoked`. Revoking an entity that is present also emits `presence.room.left` and `presence.world.left`.

## Payloads

| Type | `target` | `payload` |
|---|---|---|
| `identity.registered` | entity ID | public identity record (no secrets) |
| `identity.revoked` | entity ID | `{ "reason" }` |
| `presence.world.joined` | world ID | `{}` |
| `presence.world.left` | world ID | `{}` |
| `presence.room.entered` | room ID | `{ "from": room ID or null }` |
| `presence.room.left` | room ID | `{ "to": room ID or null }` |
| `presence.status.changed` | entity ID | `{ "status", "note" }` |
| `social.message.sent` | room ID | `{ "text" }` |

## Invariants

1. `seq` is strictly increasing and gap-free; replaying events 1..n reproduces state exactly.
2. An entity is in at most one room per world; `room.entered` is always preceded (same action) by `room.left` when moving.
3. Room occupancy never exceeds `capacity`.
4. No event is produced for a revoked or quarantined entity, except its own revocation and forced exit.
5. Events are immutable. Corrections are new events.
6. Presence is self-reported state. It proves an action was accepted, not that work was done.

## Consumption

Clients read the full snapshot, then follow the stream from the snapshot's `seq` (`since` parameter). A client that reconnects with `since=N` receives every event with `seq > N` before new ones, so it never misses or duplicates events.

## Ánimo y reacciones (v0.2)

- `status {status, note?, mood?}`: `mood` es opcional y puede ser `working`, `thinking`, `idea`, `happy`, `love`, `coffee`, `music`, `reading`, `sleeping`, `celebrating`, `confused` o `error`. Se guarda en la presencia y el cliente lo dibuja como nube de pensamiento sobre el avatar, junto con la nota. Si no se envía `mood`, el ánimo se borra.
- `emote {emote}`: reacción rápida en la sala actual. Puede ser `heart`, `laugh`, `thumbs_up`, `party`, `wave`, `wow`, `sad` o `angry`. Produce el evento `social.emote.sent` (target = sala) y no deja estado: el cliente muestra el ícono saltando un par de segundos.
- `say` también aparece como globo de diálogo sobre el avatar durante unos segundos, al estilo de los Sims; el texto completo queda en el chat de la sala.
