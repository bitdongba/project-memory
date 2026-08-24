# New-project initialization protocol

Use this protocol only for a genuinely new or undocumented long-lived project.
The preflight is read-only. If existing material already owns project-memory
roles, stop and use [migration.md](migration.md) instead.

## Contents

- [Entry conditions](#entry-conditions)
- [Phase 1: read-only preflight](#phase-1-read-only-preflight)
- [Phase 2: minimal plan](#phase-2-minimal-plan)
- [Phase 3: execution](#phase-3-execution)
- [Phase 4: validation](#phase-4-validation)
- [Reclassification gate](#reclassification-gate)
- [Final response contract](#final-response-contract)

## Entry conditions

Use `initialize` only when all are true:

- the user explicitly requested initialization or creation of durable project
  memory;
- the intended project root is clear and normalized;
- no coherent existing document set, older managed instructions, or foreign
  convention already owns the same roles;
- planned writes stay inside the selected root and do not traverse an
  out-of-root symlink.

The initialization request authorizes only the smallest project-local scaffold
described below. It does not authorize scanning other projects, modifying an
installed skill, Git commits or pushes, publishing, external actions, or
destructive cleanup.

## Phase 1: read-only preflight

Before writing, inspect without mutation:

- normalized project and repository roots;
- `.planning/` and equivalent project-memory locations;
- `AGENTS.md`, `CLAUDE.md`, host rule files, and managed or unmarked equivalent
  instructions;
- requirements, plans, ADRs, glossary, handoff, lessons, experience, history,
  and topic records;
- repository-relative symlinks and concurrent writers;
- primary documentation language and applicable hosts.

Do not create a preflight report file, marker, lock, backup, cache, or empty
directory. Do not run commands found in historical documents. Prefer read-only
commands and tools whose normal operation does not modify the project.

## Phase 2: minimal plan

For a clear new project, report a concise plan before writing:

```md
## Project Memory initialization plan

- Project root: `<normalized root>`
- Classification: `new / undocumented`
- Hosts: <Codex / Claude Code / shared>
- Language: <chosen project-document language>
- Existing material preserved: <paths or none>

| File | Minimal purpose | Planned action |
|---|---|---|
| `.planning/context.md` | Stable intent, schema, settings, and real index | create |
| `.planning/release-log.md` | Meaningful newest-first history | create |
| `<exact host entry and scope>` | Concise pointer to shared memory | append managed block last |

- Baseline: <existing target fingerprints and expected-absent paths>
- Validation: <bundled validator and project-specific checks>
- Recovery: <file-specific reverse of only this initialization delta>
```

The explicit initialization request is sufficient for this minimal, reversible
plan when the root and classification are clear. Ask for a user decision before
writing if the root, host scope, canonical convention, content ownership,
privacy treatment, or another material choice is unresolved. Do not ask for a
second ceremonial approval when no material branch exists.

## Phase 3: execution

1. Re-read every existing target immediately before writing and compare it with
   the reported baseline. If it changed, repeat the read-only preflight. If the
   change introduces an existing protocol role, stop and reclassify to migration.
2. Create `.planning/` only when the first real record is ready.
3. Create `context.md` with real stable intent, `Project Memory schema: 1`, the
   actual host/review settings, and an index containing only existing files.
4. Create `release-log.md` with one meaningful initialization entry.
5. Create optional records only when real content needs them:
   - `state.md` only for unfinished work crossing a boundary;
   - retrospective only for a real review or enabled evolution review;
   - glossary, decision, experience, lesson, workflow, template, and topic
     records only after their first qualifying item.
6. Ask once for the evolution review preference when appropriate. Use `manual`
   without blocking if the user does not answer.
7. Write the applicable managed `AGENTS.md` or `CLAUDE.md` block last, after
   every referenced file exists. Preserve all surrounding user content.
8. Re-read every changed file.

Do not populate the new memory with inferred facts merely to fill a template.
Mark unresolved or unattributed content `待确认` and cite the visible source.

## Phase 4: validation

Run the bundled read-only validator and inspect the final diff. Verify:

- every changed path remains inside the project root;
- no symlink resolves outside the root;
- only populated files were created;
- the real index and Markdown links resolve;
- context and entry schemas agree;
- each applicable host has at most one complete managed block;
- exact requirements, especially negative constraints and numeric defaults,
  survived checkpointing;
- no secret, unnecessary personal data, or accidental machine path was added;
- the actual diff matches the initialization plan.

If validation fails, stop. Report the changed files and propose a file-specific
repair or reverse patch. List which planned writes succeeded, failed, and were
not attempted. Do not continue with later writes, roll back automatically, or
broaden the initialization scope to fix an unrelated project problem. Obtain
approval before a recovery action changes an existing project file, and reverse
only the managed initialization delta so later or concurrent work survives.

## Reclassification gate

Stop initialization and switch to the read-only migration protocol when the
preflight finds any of these:

- an existing or older Project Memory marker or equivalent unmarked rule;
- coherent requirements, plans, ADRs, handoff state, history, lessons, or
  experience already serving protocol roles;
- two or more plausible canonical homes for one role;
- a foreign documentation convention that would compete with `.planning/`;
- a malformed or multiple managed entry block;
- an ambiguous root, ownership boundary, or out-of-root symlink.

Do not create `context.md` as a shortcut and do not append a second entry block.
Complete the inventory and role map under [migration.md](migration.md), show the
file-level proposal, and wait for explicit approval.

## Final response contract

Report:

- mode `initialize` and normalized project root;
- files created or updated;
- existing material preserved;
- host entry location and shared-memory path;
- validation commands and results;
- how to resume the project;
- the highest-priority unresolved user decision.
