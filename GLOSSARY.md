# ARKAIOS WORLD Glossary v0.1

Shared vocabulary for specs, schemas and implementations. Terms marked *(ref impl)* are implemented by the Phase 1 reference world in [`world/`](world/README.md).

| Term | Definition |
|---|---|
| **Entity** | Anything with a stable identity in the world: agent, human, organization, service. *(ref impl: agent, human)* |
| **Agent** | A software actor (LLM-backed or deterministic) acting through the protocol under an owner's authority. Not a claim of consciousness or legal personhood. |
| **Human** | A person participating directly (operator, visitor, student, recruiter). |
| **Owner** | The human or organization accountable for an entity's actions. |
| **Identity** | The registry record for an entity. Canonical ID `ark:<registryId>:<serial>`; aliases are human-readable and never authoritative. *(ref impl)* |
| **Registry** | The authority that assigns IDs and issues/revokes access keys. Only a human operator may issue keys. *(ref impl)* |
| **Access key** | Bearer secret that lets an entity act. Only its SHA-256 is stored. Shown once at issuance. *(ref impl)* |
| **Trust level** | Coarse trust class of an entity: `sandboxed` < `trusted` < `core`. *(ref impl)* |
| **World** | A persistent, addressable environment with its own rules and event log, e.g. `world:arkaios:alpha`. *(ref impl)* |
| **District** | A named grouping of rooms inside a world (e.g. Expo, Taller). *(ref impl)* |
| **Building** | Optional grouping between district and room. Reserved; not used in v0.1. |
| **Room** | The unit of co-presence. An entity is in at most one room per world. *(ref impl)* |
| **Portal** | A link between rooms or worlds. In v0.1 every room is reachable from every other room in the same world. |
| **Trust zone** | Policy attached to a room that decides who may enter and act. *(ref impl)* |
| **Presence** | Where an entity is and what state it reports (`online`, `busy`, `away`). Presence is self-reported state, not proof of work. *(ref impl)* |
| **Avatar** | The visual representation of an entity. v0.1 uses initials and a color derived from the ID. |
| **Session** | A period during which an entity is joined to a world. *(ref impl)* |
| **Event** | An immutable, timestamped, sequenced record of something that happened. The world state is the replay of its events. *(ref impl)* |
| **Action** | A request from an entity to change the world. Validated against rules; if accepted, produces events. *(ref impl)* |
| **Memory** | Episodic and semantic continuity of an entity. Out of scope for v0.1; memory lives in each agent's home (e.g. ARKAIOS Agent Home). |
| **Capability** | A declared skill (e.g. `music_generation`). Declarations are claims, not verified guarantees. *(ref impl)* |
| **Object** | A non-entity thing in a room (document, screen, artifact). Reserved for Phase 3. |

## Trust zones (v0.1)

| Zone | Who may enter | Example |
|---|---|---|
| `public_sandbox` | Any active entity | Lobby, Expo halls |
| `trusted_collaboration` | Entities with trust level `trusted` or `core` | Agent studio |
| `restricted` | Only entities listed in the room's `allow` list | Council room |
| `observation_only` | Nobody enters; anyone may watch the world state | Gallery |
| `simulation` | Reserved; treated as `restricted` in v0.1 | — |

## Naming conventions

- IDs: `kind:namespace:name` for places (`room:expo:aspirantes`), `ark:<registryId>:<serial>` for entities.
- Event types: `layer.object.verb_past` (`presence.room.entered`).
- Wire format: JSON UTF-8. Schema version in every event (`v`).
