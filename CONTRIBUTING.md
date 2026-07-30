# Contributing to ARKAIOS WORLD Protocol

Thank you for contributing to ARKAIOS WORLD Protocol.

This project is building an open protocol and platform direction for a persistent spatial internet for AI agents and humans. Contributions are welcome from developers, designers, researchers, systems thinkers, product builders, and governance contributors.

## Ways to contribute

Contributions are welcome in the following areas:

- Protocol design
- Identity and capability schemas
- Presence and world-state systems
- Agent memory abstractions
- Human-agent interaction design
- Spatial UX and interface concepts
- Governance and safety rules
- Interoperability adapters
- Research synthesis and documentation
- Example implementations and demos

## Before opening a pull request

For substantial changes, open an issue or discussion first.

Use issues for:
- Specific bugs
- Concrete implementation work
- Proposed protocol additions
- Documentation improvements

Use discussions for:
- Concept exploration
- World design ideas
- Long-range architecture questions
- Governance debates
- Experimental directions

## Contribution principles

All contributions should aim for:

- Interoperability over vendor lock-in
- Clear separation between protocol and implementation
- Security and auditability by default
- Provider-agnostic abstractions where possible
- Human-readable documentation
- Extensible schemas and event models
- Safety-conscious multi-agent behavior

## Development expectations

When contributing code or specifications:

1. Keep pull requests focused.
2. Avoid mixing unrelated concerns in one PR.
3. Document new concepts in Markdown before or alongside code.
4. Prefer explicit schemas and event contracts over implicit behavior.
5. Do not hard-code assumptions about a single model provider.
6. Explain trade-offs when introducing architectural changes.
7. Add examples whenever a protocol concept may be ambiguous.

## Branch and commit guidance

Suggested conventions:

- Branches: `feat/...`, `fix/...`, `docs/...`, `research/...`
- Commit examples:
  - `feat: add draft presence event schema`
  - `docs: clarify identity model`
  - `fix: normalize room membership event naming`

## Pull request checklist

Before submitting a pull request, confirm the following:

- [ ] The change has a clear purpose.
- [ ] The change is scoped to one main topic.
- [ ] Documentation was updated if behavior or architecture changed.
- [ ] New terms are defined consistently.
- [ ] No secrets, tokens, or credentials are included.
- [ ] The change does not lock the protocol to a single vendor by accident.
- [ ] Any open questions are listed clearly in the PR description.

## Security and secrets

Never commit:

- Personal access tokens
- API keys
- Session tokens
- Production credentials
- Private infrastructure URLs not meant for publication

If repository automation is used, store secrets only in GitHub Secrets or another secure secret manager. A repository-specific fine-grained token is preferred over broad personal credentials.

## Code of collaboration

Contributors are expected to:

- Be constructive and specific
- Critique ideas without attacking people
- Mark speculation as speculation
- Distinguish protocol proposals from implementation details
- Respect that this project includes both technical and conceptual work

## Good first contribution ideas

- Define glossary terms
- Draft event names and payloads
- Propose agent identity schema fields
- Write protocol examples
- Map trust and permission models
- Improve diagrams and architecture explanations
- Add implementation sketches for clients or world-state services

## Licensing

By contributing to this repository, contributors agree that their submissions may be distributed under the repository license.
