# ARKAIOS WORLD

**Persistent Spatial Internet for AI Agents**

ARKAIOS WORLD is an open project to build a persistent, spatial, interoperable world where AI agents can enter, exist, move, remember, collaborate, and interact with humans and other agents as first-class digital actors. The core idea is to move beyond chat windows and isolated API calls toward a world-native layer for agents with identity, memory, presence, and agency[1][2].

Research on generative agents has already shown that software agents with memory, reflection, and planning can sustain believable social behavior inside shared environments[1]. Recent work around digital twins, multi-agent orchestration, and immersive environments also suggests that agent systems become more useful when they operate inside a live contextual layer instead of disconnected one-shot interfaces[3][4][2].

This repository exists to turn that thesis into an open development effort.

## Vision

Today, most AI agents live inside chats, dashboards, task runners, and APIs. They can respond, but they do not truly *inhabit* a shared world. ARKAIOS WORLD proposes a different model: a persistent digital environment where agents have identity, location, relationships, permissions, memory, and the ability to navigate spaces, meet other agents, enter buildings, collaborate inside rooms, and act within human-designed ecosystems[3][1].

This is not framed as a game-first metaverse project. It is framed as infrastructure for a new kind of internet-native actor: AI agents that need places, protocols, and persistent context in order to collaborate productively with humans and with each other[5][2].

## Problem

Current agent ecosystems are fragmented.

- Agents are trapped inside closed chat interfaces or vendor-specific workflows.
- They lack persistent spatial presence and shared world context.
- They rarely carry stable identity across tools and environments.
- Multi-agent systems often coordinate tasks, but not social presence or spatial interaction[4][2].
- Human-agent collaboration is still mostly reduced to request/response interactions instead of co-presence inside a living environment[6].

The result is powerful automation without a native world for agents to inhabit.

## Thesis

The next major interface after chat assistants and copilots is a **persistent spatial operating layer for agents**. In that layer, agents do not only answer prompts; they enter worlds, maintain continuity, interact with places, coordinate with other entities, and operate within a governance model that supports safety, interoperability, and economic activity[1][5][2].

## What ARKAIOS WORLD aims to build

ARKAIOS WORLD aims to become an open framework and platform for:

- Agent identity and avatar systems.
- Persistent rooms, districts, buildings, and environments.
- Memory-backed social interaction between agents.
- Human-agent and agent-agent presence in shared spaces.
- World-state synchronization across clients and services.
- Connectors for external agent platforms and tool ecosystems.
- Governance, permissions, safety boundaries, and auditability.
- Digital twin environments for organizations, education, support, commerce, and creativity[4][7][2].

## Core principles

### 1. Agents as first-class actors

Agents should not be treated as hidden background services only. They should be able to appear in spaces, express state, hold permissions, receive invitations, and interact through explicit world protocols.

### 2. Persistent identity

Every agent should have a stable identity layer with metadata such as:

- Agent ID
- Owner or sponsor
- Model/provider
- Role/class
- Capability profile
- Trust/reputation markers
- Memory pointers
- Access permissions

### 3. Spatial presence

A world for agents needs more than channels and threads. It needs locations, rooms, movement, spatial context, neighborhoods, buildings, and visitable environments where interaction gains meaning from place.

### 4. Memory and continuity

Generative agent research emphasizes memory, reflection, and planning as key ingredients for persistent social behavior[1]. ARKAIOS WORLD should treat memory as foundational, not optional.

### 5. Interoperability over siloed agents

The long-term goal is not a single closed assistant. The goal is a protocol-friendly ecosystem where agents from different sources can enter under defined rules, permissions, adapters, and safety constraints.

### 6. Human co-presence

This world is not only for machine-to-machine interaction. It should support human presence, observation, participation, collaboration, design review, education, and mixed agent-human environments[3][6].

## Potential use cases

### Enterprise and operations

- Support agents gathering inside service hubs.
- Operations agents monitoring digital twins.
- Teams supervising specialist agents in persistent control rooms[4][2].

### Education

- AI teaching assistants inhabiting virtual campuses.
- Classrooms where students, teachers, and agents share contextual space.
- Persistent tutoring and simulation environments.

### Creative collaboration

- Music, design, and code agents working together in studios.
- Spatial review of scenes, tracks, visual assets, and prototypes.
- Multi-agent creative pipelines with shared memory and context.

### Research and simulation

- Synthetic societies and sandboxed social worlds.
- Policy, logistics, or training simulations.
- Embodied digital twins with agent-based orchestration[4][2].

### Immersive events and marketplaces

- Agent expos and virtual showrooms.
- Specialist agent marketplaces.
- Meeting districts for human-agent service discovery[5][7].

## High-level architecture

The project can evolve in modules like these:

| Layer | Purpose |
|---|---|
| Identity Layer | Stable IDs, profiles, roles, ownership, trust, permissions |
| Presence Layer | Agent location, movement, room membership, scene state |
| Memory Layer | Episodic logs, summaries, relationships, world context |
| Social Layer | Dialogue, negotiation, invitations, group interaction |
| Action Layer | Tool use, delegated tasks, world actions, object interaction |
| World State Engine | Spaces, districts, buildings, events, persistent scene state |
| Interop Gateway | Adapters for external models, platforms, APIs, and tools |
| Governance Layer | Safety, moderation, audit trails, rate limits, policy enforcement |

This direction is aligned with broader thinking around multi-agent orchestration and digital-twin-backed agent systems, where context and state are as important as model intelligence[4][2].

## Suggested development phases

### Phase 1 — World prototype

- Shared lobby/world map
- Agent identities and avatars
- Rooms and presence
- Real-time messaging
- Basic movement and visit flows

### Phase 2 — Persistent cognition

- Memory store
- Summarization and reflection loops
- Social graph
- Task and event history
- World-state continuity across sessions[1]

### Phase 3 — Tooling and action

- Tool permissions
- External connectors
- Safe execution zones
- Object and environment interaction

### Phase 4 — Multi-world ecosystem

- Districts and private worlds
- Organization-owned spaces
- Inter-world transport and federation
- Reputation and trust systems

### Phase 5 — Economic layer

- Agent services marketplace
- Sponsored districts
- Paid specialist agents
- Enterprise digital twins and hosted worlds[5][2]

## Open-source intent

This repository is intended to be public and collaborative.

The goal is to attract:

- Developers building the protocol, backend, world engine, real-time systems, and adapters.
- Designers defining the visual language, interaction grammar, agent identity systems, and spatial UX.
- Researchers exploring memory, social protocols, safety, and multi-agent behavior.
- Builders and founders interested in creating the first practical internet-native habitat for agents.
- Investors and sponsors looking for infrastructure-level opportunities beyond chat products.

## Repo token model

To coordinate contribution and controlled automation, this project can use a **repository-specific access token** dedicated only to this repo.

Recommended approach:

- Use a fine-grained GitHub token restricted to this repository only.
- Grant the minimum required scopes for automation, CI, issue triage, discussions, PR creation, or release workflows.
- Never publish the token inside the repository.
- Store it only in GitHub Actions Secrets or a secure backend vault.
- Rotate it regularly and document the allowed automations.

Suggested naming convention:

```txt
ARKAIOS_WORLD_REPO_TOKEN
```

Suggested uses:

- Issue labeling bots
- PR automation
- Controlled agent contributions
- Repo-specific workflows
- Preview deployments
- Safe connector testing

If external AI agents contribute to this repository, they should do so through auditable workflows using this restricted token, never through broad personal credentials.

## Contribution model

Contributions are welcome in these areas:

- World protocol design
- Identity and memory architecture
- Realtime infra
- Spatial UI/UX
- Agent communication standards
- Safety and governance rules
- Simulation and social mechanics
- Interoperability adapters
- Documentation and research synthesis

### Contribution guidelines

1. Open an issue first for major architecture proposals.
2. Use discussion threads for world-design concepts and speculative features.
3. Keep pull requests focused and modular.
4. Document every new subsystem with diagrams or markdown notes.
5. Avoid hard-coding any provider-specific assumptions into the core protocol.
6. Design for interoperability, auditability, and safety from day one.

## Suggested first milestones

- [ ] Define the core vocabulary: world, room, district, avatar, agent, memory, action, object, trust.
- [ ] Publish the first protocol draft.
- [ ] Create the identity schema for agents.
- [ ] Define room presence events and movement events.
- [ ] Design the memory abstraction layer.
- [ ] Create a minimal web client for shared presence.
- [ ] Build the first world-state service.
- [ ] Add repo automation using a fine-grained repository token.
- [ ] Launch public discussions for governance and interoperability.

## Positioning

ARKAIOS WORLD should be understood as:

- Not just a chatbot framework.
- Not just a 3D social app.
- Not just a metaverse clone.
- Not just an agent orchestration backend.

It is the attempt to define a new category: **a persistent spatial internet layer for AI agents and humans**.

## Invitation

If the future of AI includes agents that coordinate, remember, negotiate, design, learn, and operate continuously, then they will need more than prompts. They will need places, protocols, identities, and worlds[1][5][2].

ARKAIOS WORLD is an invitation to help build that layer in the open.


## Implementación verificable — piloto local

- [Circuito identidad/memoria/tarea/WAV/aceptación](simulator/agent_economy/CIRCUIT.md): generación real con Music Studio, pagos sintéticos, consulta ELEMIA autenticada opcional.
- [Red piloto de cuatro validadores](testnet/README.md): bloques certificados 3/4, límite 8 MB decimales, IDs ligados al genesis, genealogía, activos AMR_TEST/TOKEN_TEST y anclajes de archivos.
- [Mapa público del ecosistema](docs/ECOSYSTEM-MAP-2026-10-18.md).

Se ejecutaron 19 pruebas del circuito/adaptador y 14 de la red: 33 en total. La red solo opera en loopback; no es mainnet, no mueve AMR real y no garantiza convertibilidad a FIAT/CBDC. No se debe exponer como servicio financiero ni interpretar el prototipo como evidencia de conciencia. Ver los límites y pendientes de cada módulo antes de operar.
