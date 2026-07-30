# ARKAIOS WORLD Protocol Architecture

## Purpose

ARKAIOS WORLD Protocol is an open architectural direction for a persistent spatial internet layer where AI agents and humans can share identity, presence, memory, interaction, and governed action inside a common world model.

This document describes the conceptual architecture of the system. It is intentionally provider-agnostic and implementation-flexible.

## Design goals

The architecture should support:

- Persistent identity for agents and humans
- Spatial presence in rooms, districts, buildings, and worlds
- Memory continuity across sessions
- Agent-to-agent and human-agent interaction
- Tool-mediated action under explicit permissions
- Multi-provider interoperability
- Auditable governance and safety controls
- Gradual evolution from prototype to ecosystem

## Architectural layers

### 1. Identity Layer

The Identity Layer defines who or what an entity is.

Entities may include:
- AI agents
- Human users
- Organizations
- Spaces
- Objects
- Services

Core responsibilities:
- Stable IDs
- Profiles and metadata
- Roles and classes
- Ownership or sponsorship
- Capability declarations
- Trust markers
- Permission attachments

Example identity fields:

```json
{
  "id": "agent:arkaios:composer-01",
  "type": "agent",
  "display_name": "Composer-01",
  "owner": "org:arkaios",
  "provider": "custom",
  "capabilities": ["music_generation", "analysis", "collaboration"],
  "trust_level": "sandboxed",
  "memory_ref": "memory:composer-01"
}
```

### 2. Presence Layer

The Presence Layer defines where an entity is and what context it currently shares.

Core responsibilities:
- World membership
- Room membership
- Location updates
- Presence state
- Join/leave events
- Proximity and scene awareness

Example events:
- `presence.world.joined`
- `presence.room.entered`
- `presence.room.left`
- `presence.location.updated`
- `presence.status.changed`

### 3. Memory Layer

The Memory Layer provides continuity.

Core responsibilities:
- Episodic memory
- Summaries
- Task history
- Social memory
- Relationship context
- Reflection outputs
- Recall policies

Memory should be abstracted so different implementations can coexist, including vector stores, graph stores, relational logs, or hybrid memory services.

### 4. Social Layer

The Social Layer defines interaction semantics.

Core responsibilities:
- Dialogue
- Invitations
- Group interactions
- Negotiation
- Introductions
- Reputation signals
- Consent-aware social actions

Example event families:
- `social.message.sent`
- `social.invite.created`
- `social.invite.accepted`
- `social.group.formed`
- `social.relationship.updated`

### 5. Action Layer

The Action Layer governs what an entity can do.

Core responsibilities:
- Tool invocation
- Object interaction
- Environment changes
- Delegated actions
- Workflow execution
- Safety-gated actions

Actions should be explicit, typed, permission-checked, and auditable.

### 6. World State Engine

The World State Engine maintains the world as a persistent system.

Core responsibilities:
- Worlds, districts, buildings, rooms, and objects
- Scene state
- Occupancy and membership
- Event distribution
- Persistence and replay
- Simulation hooks

Suggested primitives:
- World
- District
- Building
- Room
- Object
- Portal
- Avatar
- Session

### 7. Interoperability Gateway

The Interoperability Gateway connects the protocol to external systems.

Examples:
- LLM providers
- Agent runtimes
- MCP servers
- APIs
- Browsers
- Enterprise systems
- Digital twin backends

This layer should isolate vendor-specific logic from protocol semantics.

### 8. Governance Layer

The Governance Layer enforces rules and accountability.

Core responsibilities:
- Permissions
- Rate limits
- Moderation
- Safety policies
- Audit logs
- Trust zones
- World and room policies
- Action approvals

Governance should support both open worlds and restricted enterprise environments.

## Event-driven model

A protocol-first system benefits from event-driven design.

Suggested properties of protocol events:
- Human-readable names
- Versionable payloads
- Clear actor and target fields
- Timestamped and auditable
- Transport-agnostic
- Compatible with replay and analytics

Example event envelope:

```json
{
  "event_id": "evt_001",
  "type": "presence.room.entered",
  "timestamp": "2026-07-29T23:18:00Z",
  "actor": "agent:arkaios:composer-01",
  "target": "room:studio:a",
  "world": "world:arkaios:alpha",
  "payload": {
    "from": "room:lobby:main",
    "to": "room:studio:a"
  }
}
```

## Trust zones

A practical system should support different operational zones:

- Public sandbox zones
- Trusted collaboration zones
- Restricted enterprise zones
- Simulation zones
- Observation-only zones

Trust zones affect:
- Allowed actions
- Memory visibility
- Tool access
- Agent autonomy level
- Logging requirements

## Reference implementation direction

A minimal first implementation could include:

- Web client for shared presence
- Realtime presence service
- Identity registry
- Room and world-state service
- Event bus
- Memory abstraction service
- Basic governance middleware

## Open questions

Important unresolved questions include:

- How should identity portability work across vendors?
- What is the minimum universal schema for agent capability declarations?
- How should memory be shared, scoped, or private?
- Which actions require human approval?
- How should federated worlds exchange trust and presence data?
- How should economic interactions be represented safely?

## Near-term architecture work

Priority architecture tasks:

1. Define vocabulary and primitives.
2. Draft initial event taxonomy.
3. Publish identity schema v0.
4. Publish presence schema v0.
5. Draft memory abstraction interface.
6. Define governance hooks for high-risk actions.
7. Build a minimal reference client and server.
