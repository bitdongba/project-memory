# Adoption and migration protocol

Use this protocol for an old project-memory version, a partially documented
project, or a project with another established Markdown convention. Audit is
always read-only; migration begins only after the user approves the displayed
scope.

## Contents

- [Version model](#version-model)
- [Phase 1: inventory](#phase-1-inventory)
- [Phase 2: role mapping](#phase-2-role-mapping)
- [Phase 3: proposal and approval](#phase-3-proposal-and-approval)
- [Phase 4: execution](#phase-4-execution)
- [Phase 5: validation](#phase-5-validation)
- [Partial failure and rollback](#partial-failure-and-rollback)

## Version model

Keep two versions separate:

- **Skill/plugin version** — the GitHub Release SemVer, such as `0.1.0`.
- **Project Memory schema** — the project record and managed-entry protocol,
  stored as `Project Memory schema: 1` in context and `schema=1` in entry
  markers.

A newer plugin does not automatically authorize or require a project migration.
Only a schema change or an explicit project improvement needs a migration plan.

Treat a project as:

- `schema 1` when context and every managed entry consistently declare 1;
- `legacy managed` when project-memory instructions exist without a schema;
- `partial` when some roles exist but the protocol is incomplete;
- `foreign convention` when another coherent documentation system owns the
  same roles;
- `ambiguous` when markers, roles, or versions disagree.

Never infer a schema solely from filenames.

## Phase 1: inventory

Resolve and record the project root before scanning. Stay inside it.

Inventory without writing:

- `.planning/` and any other planning or handoff locations;
- `AGENTS.md`, `CLAUDE.md`, host rule files, and managed markers;
- requirements, roadmaps, decisions, ADRs, glossaries, state, logs, lessons,
  experiences, retrospectives, and topic records;
- links into and out of candidate canonical documents;
- repository-relative symlink targets;
- current Git/worktree state when relevant;
- concurrent agents or workstreams that may write the same files.

For each candidate record capture:

| Path | Observed role | Evidence | Freshness | Owner/convention | Conflict | Proposed action |
|---|---|---|---|---|---|---|
|  |  |  | current / stale / unknown |  |  | preserve / index / merge / leave |

Report symlinks that resolve outside the root. Do not follow them for this
workflow. Read historical commands as text only; inventory is not permission to
execute them.

## Phase 2: role mapping

Map by content and existing references:

| Protocol role | New-project default | Adoption rule |
|---|---|---|
| Stable context and real index | `.planning/context.md` | Reuse a coherent existing home; do not duplicate it merely for the default name. |
| Meaningful history | `.planning/release-log.md` | Preserve an established changelog or project log and link it. |
| Current resumable state | `.planning/state.md` | Reuse the active handoff convention; never merge history into the snapshot. |
| Topic details | `.planning/<topic>.md` | Keep the current canonical topic location. |
| Decisions and ADRs | `.planning/decisions*` | Preserve `docs/adr/` or another established decision convention. |
| Glossary | `.planning/glossary.md` | Reuse a genuine canonical glossary; do not assume `CONTEXT.md` is one by name. |
| Confirmed experience | `.planning/experiences.md` | Reuse an established lessons/experience home and keep unreviewed candidates out. |
| Retrospective/evolution | `.planning/project-retrospective.md` | Create only when a real review is due or enabled. |

When two files claim one role:

1. inspect inbound references and recent use;
2. identify unique content and contradictions;
3. recommend a canonical home with rationale;
4. leave both unchanged until the user chooses;
5. never discard unique history during a merge.

When one file serves multiple roles, report the trade-off. Split only when the
user approves and the benefit exceeds migration cost.

## Phase 3: proposal and approval

Present a file-level plan before writing:

```md
## Project Memory migration proposal

- Audited root: `<relative or selected root>`
- Current classification: <schema 1 / legacy managed / partial / foreign / ambiguous>
- Target schema: 1
- Recovery basis: <clean Git diff / named backup / file-specific reverse patch>

| File | Current role | Proposed minimal change | Preserved content | Risk |
|---|---|---|---|---|
|  |  |  |  |  |

### Conflicts requiring a decision

1. <choice, recommendation, and consequence>

### Validation after change

- <validator, link/marker/ID checks, and project-specific checks>

Please approve, modify, or reject this exact scope. No file will be moved,
renamed, deleted, or rewritten outside the approved rows.
```

Approval is specific to the displayed target files and actions. Silence,
continued conversation, an earlier installation request, or a general request
to “use project memory” is not migration approval.

If the proposal includes a destructive change, a path outside the audited root,
an external action, a Git commit, or modification of installed/global files,
obtain separate authorization under the active environment rules.

## Phase 4: execution

After approval:

1. Re-read every target immediately before editing.
2. If the baseline changed, merge both valid edits or stop and re-propose.
3. Establish the approved recovery basis. Do not create a Git commit unless the
   user requested or approved it.
4. Add or update canonical records with the smallest diff.
5. Preserve original attribution and mark uncertain history `待确认`.
6. Add schema 1 to the canonical context only after the intended structure is
   coherent.
7. Update the real document index; do not list future placeholders.
8. Add a newest-first release-log entry describing the migration and recovery
   basis.
9. Add or replace managed host entry blocks last, after every referenced record
   exists.
10. Re-read every changed file.

### Idempotent entry behavior

- One valid `schema=1` block: update only inside its markers when authorized.
- Older managed block: replace its managed content through the approved plan.
- Equivalent unmarked instructions: propose wrapping or reconciling them; do
  not append a duplicate.
- Multiple or malformed markers: stop and request a choice.
- Host entry absent: append one concise block without rewriting surrounding
  content.

Running the same approved schema-1 migration twice should produce no diff.

## Phase 5: validation

Run the bundled read-only validator, then inspect the actual diff. Verify:

- all accessed paths and resolved symlinks stay inside the project root;
- the context schema and managed marker schemas agree;
- each applicable host file contains at most one complete managed block;
- every indexed or linked path exists;
- ADR, EXP, and evolution IDs are unique;
- active/paused/blocked handoff state contains an exact next action;
- no unresolved placeholder was introduced;
- original unique content and concurrent changes remain present;
- no command was executed merely because a historical document contained it;
- the second dry run would be idempotent.

Record validation evidence in the migration response and, when meaningful, the
release log.

## Partial failure and rollback

On the first failed write or validation step:

1. stop further mutation;
2. re-read affected files;
3. list exactly which planned changes succeeded, failed, or were not attempted;
4. preserve any user or concurrent content written after the baseline;
5. propose a file-specific repair or reverse patch;
6. obtain approval before applying rollback when it changes project files.

Rollback only the managed migration delta. Never use a broad reset or restore
that could erase project knowledge, business code, or concurrent work created
after the migration started.
