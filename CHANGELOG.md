# Changelog

All notable changes to Project Memory are documented in this file.

The project uses semantic versioning. Skill frontmatter intentionally contains only the fields consumed by skill hosts; release versions live in Git tags, plugin manifests, release notes, and artifact names.

## Unreleased

- No changes yet.

## 0.1.0 - 2026-08-24

Initial public preview.

### Added

- Dual plugin manifests for Codex and Claude Code, with the same skill source under `skills/project-memory/`.
- Standalone installation for Codex and Claude Code.
- Markdown project memory for stable context, requirements, decisions, terminology, handoff state, history, retrospectives, and reusable experience.
- Evidence-aware separation of verified facts, user decisions, assumptions, and open questions.
- Conditional clarification for material ambiguity.
- Immediate checkpoints for confirmed material requirements and decisions.
- Lazy glossary, ADR-style decision records, precise handoff state, and human-reviewed reusable experience.
- Read-only audit and in-place migration flows for existing projects and projects created by earlier versions.
- Governed evolution reviews with evidence, options, individual user decisions, reversible current-project trials, outcome validation, and separate adoption decisions.
- Deterministic project-memory validation fixtures and tests.

### Security and privacy

- No background service, telemetry, MCP server, lifecycle hooks, or automatic update mechanism.
- No silent cross-project scanning, self-modification, publishing, or installed-copy updates.
- Project memory excludes secrets and prefers redacted references and repository-relative paths.
