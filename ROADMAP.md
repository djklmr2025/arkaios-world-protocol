# ARKAIOS WORLD Protocol Roadmap

## Roadmap intent

This roadmap describes a staged path from concept to open protocol and early reference implementations.

It is designed to keep the project grounded, modular, and open to public contribution.

## Phase 0 — Foundation

Goal: establish the language, scope, and public collaboration structure.

Deliverables:
- Public repository setup
- README and project vision
- Contribution guidelines
- Architecture draft
- Core glossary draft
- Initial discussions and issue taxonomy

Success criteria:
- Repository is publicly understandable
- New contributors can identify how to participate
- Core vision and boundaries are documented

## Phase 1 — Protocol vocabulary

Goal: define the foundational concepts of the world.

Deliverables:
- Glossary of terms
- Entity taxonomy
- World primitives
- Initial event naming conventions
- Versioning strategy

Candidate concepts:
- World
- District
- Building
- Room
- Portal
- Object
- Agent
- Human
- Avatar
- Session
- Memory
- Capability
- Trust zone

Success criteria:
- Contributors can discuss the system using shared terms
- Draft schemas can reference stable concept names

## Phase 2 — Identity and presence

Goal: establish who is in the world and where they are.

Deliverables:
- Identity schema v0
- Presence schema v0
- Join/leave/move event draft
- Trust and permission model draft
- Basic room membership rules

Success criteria:
- Entities can be represented consistently
- Presence events can be tracked and replayed

## Phase 3 — Memory and social interaction

Goal: define continuity and interaction semantics.

Deliverables:
- Memory abstraction draft
- Social event taxonomy
- Relationship model draft
- Invitation and group interaction patterns
- Context retention policies

Success criteria:
- A minimal system can preserve continuity across sessions
- Social interactions are explicit and inspectable

## Phase 4 — Action and governance

Goal: support meaningful action without losing safety.

Deliverables:
- Action schema v0
- Tool permission model
- Governance middleware design
- Audit log strategy
- Human approval hooks for sensitive actions

Success criteria:
- Actions are typed and permission-checked
- High-risk actions can be reviewed and controlled

## Phase 5 — Reference implementation

Goal: prove the protocol through a minimal working system.

Deliverables:
- Minimal web client
- Realtime presence backend
- Identity registry
- World-state service
- Event bus or event stream
- Simple world with lobby and rooms

Success criteria:
- Multiple entities can join the same world
- Presence and movement can be observed in real time
- World state persists between sessions

## Phase 6 — Interoperability

Goal: connect external agent systems into the world.

Deliverables:
- Adapter specification
- External provider bridge examples
- MCP integration experiments
- Browser or tool action connectors
- Federation concepts for multi-world connectivity

Success criteria:
- External agent runtimes can participate through defined interfaces
- Provider-specific logic remains isolated from the protocol core

## Phase 7 — Ecosystem growth

Goal: turn the protocol into a living builder ecosystem.

Deliverables:
- Example worlds
- Public demos
- Agent profiles and templates
- Design system for world interfaces
- Documentation site
- Showcase projects

Success criteria:
- Independent contributors build experiments on top of the protocol
- The repo evolves into an ecosystem, not just a concept document

## Priority backlog

Recommended first public tasks:

- [ ] Publish `GLOSSARY.md`
- [ ] Draft `identity.schema.json`
- [ ] Draft `presence.events.md`
- [ ] Draft `memory-interface.md`
- [ ] Define trust zone levels
- [ ] Open governance discussion threads
- [ ] Create minimal websocket/world-state prototype
- [ ] Publish first reference client mockup

## Working style

This roadmap should be treated as directional rather than rigid.

The project should prefer:
- Small public milestones
- Clear specs before complexity
- Open discussion before irreversible design choices
- Multiple interoperable implementations over one monolith
