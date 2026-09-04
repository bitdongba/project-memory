# Changelog

All notable changes to Project Memory are documented in this file.

The project uses semantic versioning. Skill frontmatter intentionally contains only the fields consumed by skill hosts; release versions live in Git tags, plugin manifests, release notes, and artifact names.

## Unreleased

- No changes yet.

## 0.2.0 - 2026-09-04

### Added

- An optional ruleset-1 contract, versioned independently from schema 1, for a
  stable Context boot contract, typed canonical-role index, and deterministic
  write preflight.
- A read-only router that resolves explicit statement kinds only through the
  audited role index and never authorizes a write.
- Explicit health validation with stable text/JSON output, four severity
  levels, approved-baseline comparison, and a no-regression ratchet.
- Anonymous mutation fixtures for legacy compatibility, healthy ruleset
  structure, Context drift, history ordering, numeric-heading regression, and
  missing state completion signals.

### Changed

- Context templates no longer invite current focus, next milestones, blockers,
  releases, deployments, PIDs, build hashes, or other transient state.
- Ruleset opt-in is an atomic, item-approved migration of the context
  declaration, typed index, conflicting maintenance instructions, and every
  applicable host entry; legacy schema-1 projects remain valid.
- Ruleset health adds deterministic release-order and state-completion errors,
  plus review or warning diagnostics for heuristic drift signals.
- Ruleset parsing now keeps both core roles fixed to `.planning/context.md`,
  validates every indexed canonical Markdown target, follows CommonMark heading
  and fence indentation, and binds numeric finding signatures to section scope.

### Security and governance

- The validator and router are read-only, never auto-fix content, and never
  create, accept, refresh, or weaken a health baseline.
- Ruleset opt-in defaults to advisory behavior. Hooks, CI workflows, required
  checks, commits, publishing, and installed-copy updates remain separate,
  explicitly approved actions.

## 0.1.1 - 2026-08-24

### Added

- Bilingual human workflows for initializing genuinely new projects and
  migrating existing or partially documented projects.
- A dedicated agent initialization protocol with a read-only eligibility
  preflight and automatic reclassification to migration when existing material
  already serves project-memory roles.

### Changed

- Existing-project migration now requires a strict zero-write audit, revisioned
  `MIG-*` items, item-by-item user decisions, dependency closure, and baseline
  revalidation before execution.
- Validation and recovery now compare actual changes with the approved item set,
  stop at the first unexpected delta or failure, and require separate approval
  for file-changing recovery actions.
- Partial migration approval must be dependency- and validation-closed; atomic
  execution groups cannot be split into an invalid intermediate project.
- The validator now interprets inline-code document-index paths relative to the
  project root while preserving standard Markdown link semantics.
- Standalone Skill release archives now include the MIT license.

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
