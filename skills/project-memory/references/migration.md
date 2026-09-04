# Adoption and migration protocol

Use this protocol for an old project-memory version, a partially documented
project, or a project with another established Markdown convention. The audit
and approval stages are strictly zero-write. Migration begins only after the
user decides the displayed `MIG-*` items.

## Contents

- [Version and route model](#version-and-route-model)
- [Zero-write audit contract](#zero-write-audit-contract)
- [Phase 1: inventory](#phase-1-inventory)
- [Phase 2: role mapping](#phase-2-role-mapping)
- [Phase 3: proposal and item decisions](#phase-3-proposal-and-item-decisions)
- [Phase 4: approved execution](#phase-4-approved-execution)
- [Phase 5: validation](#phase-5-validation)
- [Partial failure and recovery](#partial-failure-and-recovery)
- [Agent state transitions](#agent-state-transitions)

## Version and route model

Keep these version dimensions separate:

- **Skill/plugin version** — the GitHub Release SemVer, such as `0.1.0`.
- **Project Memory schema** — the project record and managed-entry protocol,
  stored as `Project Memory schema: 1` in context and `schema=1` in entry
  markers.
- **Project Memory ruleset** — an optional behavioral and health contract,
  stored as `Project Memory ruleset: 1` in context and `ruleset=1` after
  `schema=1` in every applicable entry marker. Its absence is valid legacy
  schema-1 behavior.

A newer plugin does not automatically authorize or require a project migration.
Only a schema change, ruleset opt-in/change, or an explicit project improvement
needs a migration plan. A ruleset version does not bump the schema when record
structure remains compatible.

Classify the inspected project as:

- `initialize-eligible` when no existing material serves a project-memory role
  and no marker, equivalent host rule, foreign convention, or disputed role
  needs reconciliation;
- `schema 1 legacy` when context declares schema 1, has no ruleset, and every
  managed entry consistently uses the legacy schema-1 marker;
- `schema 1 / ruleset 1` when context declares both values, its role index is
  deterministic, and every managed entry consistently declares both values;
- `legacy managed` when project-memory instructions exist without a schema;
- `partial` when some roles exist but the protocol is incomplete;
- `foreign convention` when another coherent documentation system owns the
  same roles;
- `ambiguous` when roots, markers, roles, ownership, schema, ruleset, or
  maintenance instructions disagree.

Ordinary source files or a README that does not serve a project-memory role do
not prevent initialization. Any need to reuse, map, merge, wrap, replace, move,
rename, delete, or choose between existing project-memory material requires the
migration route. Never infer a schema or role solely from a filename.

If an initialization preflight discovers a migration condition, keep the work
read-only, report the reclassification, and continue with this audit. If a
migration audit instead proves `initialize-eligible`, return to
[initialization.md](initialization.md); write only when the user's current request
explicitly authorizes initialization.

If the project is coherent schema 1, with or without ruleset 1, and the user has
not requested a specific project improvement, report that no migration is
needed and stop with zero writes. A newer skill version or availability of
ruleset 1 alone is not a migration item.

## Zero-write audit contract

Until an approved, dependency- and validation-closed executable subset passes
the execution preflight, the project mutation count must remain zero. The audit
and approval stages must not create, modify, delete, move, or rename any project
path; they also must not touch, format, or rewrite one. This prohibition
includes:

- an audit report, plan, backup, lock, marker, cache, temporary project file, or
  empty directory;
- a formatter, generator, installer, validator mode, or Git command that changes
  the worktree, index, metadata, or ignored files;
- following a symlink outside the selected project root;
- changing an installed skill, another project, global configuration, remote
  service, Git history, or published artifact.

Use read-only inspection tools. Keep the audit report and proposal in the
conversation; writing a report into the project would violate the audit. If a
read-only guarantee cannot be established for a command, do not run it.

The audit request itself grants no write authority. Silence, continued
conversation, installation of a newer skill, or a broad instruction such as
“use Project Memory,” “upgrade this project,” or “apply the skill” is not
migration approval.

## Phase 1: inventory

Resolve and record the selected project root, repository root, and real paths
before scanning. Stay inside the selected root and report any boundary ambiguity.

Inventory without writing:

- `.planning/` and any other planning or handoff locations;
- `AGENTS.md`, `CLAUDE.md`, nested host rule files, managed markers, and
  equivalent unmarked instructions, including the scope of each entry file;
- every instruction that tells a person or agent when and where to maintain
  context, state, history, topics, releases, deployment facts, or other project
  memory, including instructions embedded inside the records themselves;
- requirements, roadmaps, decisions, ADRs, glossaries, state, logs, lessons,
  experiences, retrospectives, and topic records;
- links into and out of candidate canonical documents;
- repository-relative symlink targets;
- current Git/worktree state when relevant;
- concurrent agents or workstreams that may write the same files.

Capture an identifiable audit baseline. Prefer the current Git commit plus
worktree diff when available; otherwise record content fingerprints for every
candidate and the absent state of proposed new paths. Record the baseline in the
proposal so it can be checked again immediately before execution.

For each candidate record capture:

| Path | Observed role | Evidence | Freshness | Owner/convention | Conflict | Baseline |
|---|---|---|---|---|---|---|
|  |  |  | current / stale / unknown |  |  | commit/diff or fingerprint |

Report symlinks that resolve outside the root. Do not follow them for this
workflow. Read historical commands as text only; inventory is not permission to
execute them. Report maintenance-instruction collisions with both exact sources.
In particular, a rule that sends current focus, milestones, blockers, release
versions, deployment state, PID, build hashes, or dated operational facts into
`context.md` conflicts with the ruleset-1 stable boot contract even when a newer
heading elsewhere says context is stable. Do not decide that a nearby or newer
instruction silently overrides the old one. End the audit report with an
explicit statement that no project path was written.

## Phase 2: role mapping

Map by content and existing references:

| Protocol role | New-project default | Adoption rule |
|---|---|---|
| Stable boot contract and real role index | `.planning/context.md` | Reuse a coherent existing home; do not duplicate it merely for the default name. Current focus, milestones, blockers, dated events, and operational snapshots are not part of this role. |
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

## Phase 3: proposal and item decisions

Give the proposal an ID and revision. Give every independently decidable change
a stable ID beginning with `MIG-`, such as `MIG-01`. Present all items as
`pending` before asking for decisions:

```md
## Project Memory migration proposal

- Plan: `PM-MIG-<date-or-slug>` revision 1
- Audited root: `<normalized selected root>`
- Audit baseline: `<Git commit + dirty diff identity, or file fingerprints>`
- Current classification: <schema 1 legacy / schema 1 + ruleset 1 / legacy managed / partial / foreign / ambiguous>
- Target schema: 1
- Target ruleset: <unchanged / absent / 1>
- Audit writes: `0`
- Recovery basis: <pre-existing clean Git baseline / file-specific reverse patch / separately approved MIG item that creates a named backup>

| Item | Target path(s) | Action | Exact expected delta | Must preserve | Dependencies / execution group | Risk / separate authority | Recovery action | Validation | Decision |
|---|---|---|---|---|---|---|---|---|---|
| MIG-01 |  | create / update / index / merge / wrap / replace managed block / leave |  |  | none |  |  |  | pending |

### Conflicts requiring a decision

1. <choice, recommendation, and consequence>

Please approve, modify, reject, or defer each `MIG-*` item. No project path will
change until the approved items and their dependencies form a valid executable
subset.
```

Each item must state:

- its target path and inspected fingerprint or absent baseline;
- its exact action and expected hunk or bounded delta, not merely a goal;
- content and marker regions that must remain byte-for-byte unchanged;
- dependencies on other items and any atomic execution group needed to leave a
  valid project state;
- risks and any separate authority required;
- a file-specific recovery action that preserves later or concurrent work;
- validation checks and its decision state.

A recovery basis is evidence, not implicit permission to create another file or
Git commit. Prefer the captured read-only baseline and item-specific reverse
deltas. If a new backup is required, model it as its own `MIG-*` item with an
exact target, expected delta, risk, validation, and recovery action; obtain any
separate authority before creating it.

Valid decision states are `pending`, `approved`, `modified`, `rejected`, and
`deferred`. Approval is item-by-item. A user may decide several items in one
response, but each decision must map unambiguously to an item ID. Never fill
undecided states from silence or a general request.

When the user modifies an item, produce a new plan revision and return it to
`pending` until the revised item is explicitly approved. Any change to an
item's path, action, expected delta, preservation rule, dependency, risk,
recovery action, or inspected baseline also increments the revision and expires
that item's prior approval. Unaffected items may retain approval only when their
own fields and dependencies are unchanged and the revised proposal states this
explicitly.

Partial approval is executable only when the approved subset is both
dependency-closed and validation-closed. Every member of an atomic execution
group must be approved. Before requesting decisions, reason over the proposed
final tree and group changes that cannot independently leave the project valid;
for example, do not treat creation of schema-required records as independently
executable when an applicable required host entry is rejected. If the user's
decisions do not form a valid executable subset, keep all affected items
unchanged, explain the minimum additional or revised decisions needed, and wait.
Never apply an approved item merely to discover a known closure failure during
validation.

For a ruleset-1 opt-in, use one atomic execution group containing all of the
following applicable deltas:

1. add `Project Memory ruleset: 1` and an explicit enforcement level to
   `context.md`;
2. make the context document index deterministic with the exact
   `stable-intent`, `protocol-setting`, `resumable-state`, `historical-event`,
   and `topic-detail` role tokens for files that actually exist; both core roles
   must map to `.planning/context.md`, while established history, state, and
   topic locations may remain project-relative canonical targets;
3. remove, replace, or explicitly reconcile every old maintenance instruction
   that conflicts with the stable boot contract;
4. change every applicable managed host marker and block to the exact
   `schema=1 ruleset=1` variant.

Do not enable only the context declaration, only one host, or only the entry
text. If any member is rejected, deferred, changed, or has baseline drift, leave
the entire group untouched and revise the plan. Resolving a collision may mean
preserving unique historical content while replacing only its active
maintenance instruction; it never authorizes automatic deletion or relocation
of the surrounding content.

Rejected or deferred items and anything depending on them remain untouched.
Destructive changes, paths outside the audited root, external actions, Git
commit or push, publishing, installed/global files, and modification of the
reusable skill require separate explicit authority; item approval alone never
grants it. Treat a stored health baseline, a threshold or exemption change, a
pre-commit hook, CI workflow, and required branch check as separate items.
Ruleset opt-in does not authorize any of them, and an Agent-run check must not
be described as external enforcement.

## Phase 4: approved execution

Before the first write, perform a read-only preflight:

1. Re-read every approved target and dependency.
2. Compare each path with the exact approved baseline, including expected
   absence for a new file.
3. Confirm the recovery action remains usable.
4. Confirm the approved item set is dependency-closed, validation-closed, and
   contains every member of each atomic execution group; separately authorized
   actions must have their own current approval.
5. Confirm every planned path and resolved symlink stays inside the audited root.
6. Resolve every proposed Markdown link relative to its containing file and
   check the in-memory expected final tree against the structural rules. Do not
   write a temporary draft inside the project.

If any approved baseline changed, do not merge automatically and do not execute
that item. Affected approvals expire: re-audit the affected items, increment the
plan revision, and show each revised item for a new decision. If the change
affects a dependency or shared target, stop every dependent item as well.

After preflight passes:

1. Execute only `approved` items from the current plan revision.
2. Add or update canonical records with the smallest exact diff.
3. Preserve original attribution and mark uncertain history `待确认`.
4. Add schema 1 only after the approved canonical structure is coherent. Add
   ruleset 1 only as its complete atomic opt-in group; never create a mixed
   context/entry state, even temporarily across a validation boundary.
5. Update only the real document index; never list future placeholders. For
   ruleset 1, preserve exact machine-readable role tokens and refuse ambiguous
   role-to-path mappings.
6. Keep release-log wording accurate to the current state; do not claim a
   migration was validated before validation passes.
7. Add or replace approved managed host entry blocks last, after every referenced
   record exists. Preserve marker-external bytes.
8. Re-read every changed file and compare its actual delta with the approved
   item before continuing.

At the first unplanned path, hunk, side effect, or failed write, stop all later
mutation and enter partial-failure handling.

### Idempotent entry behavior

- One valid legacy `schema=1` block: preserve it unless an in-place update or
  complete ruleset opt-in was approved.
- One valid `schema=1 ruleset=1` block: update only inside its markers when
  authorized and context declares the same ruleset.
- Older managed block: replace its managed content through the approved plan.
- Equivalent unmarked instructions: propose wrapping or reconciling them; do
  not append a duplicate.
- Multiple or malformed markers: keep them unchanged until the user chooses.
- Host entry absent: append one concise approved block without rewriting
  surrounding content.

## Phase 5: validation

Run the bundled read-only validator, then inspect the actual diff. Verify:

- all accessed paths and resolved symlinks stay inside the project root;
- the context schema and managed marker schemas agree;
- the context ruleset and every applicable managed marker ruleset agree; schema
  1 without any ruleset remains valid, while mixed absent/present values do not;
- a ruleset-1 role index maps `stable-intent` and `protocol-setting` to
  `.planning/context.md`, maps each other non-topic role to exactly one
  canonical path, and gives every requested topic path exactly one
  `topic-detail` row;
- each applicable host file contains at most one complete managed block;
- marker-external bytes and every declared preserved region are unchanged;
- every indexed or linked path exists, and every indexed canonical Markdown
  target received the applicable structural and health checks;
- ADR, EXP, and evolution IDs are unique;
- active/paused/blocked handoff state contains an exact next action;
- no unresolved active maintenance instruction contradicts the ruleset-1
  stable boot contract;
- no unresolved placeholder, secret, unnecessary personal data, or accidental
  absolute path was introduced;
- original unique content and concurrent changes remain present;
- no command was executed merely because a historical document contained it;
- every successful approved item produced its exact expected delta, and no
  rejected, deferred, pending, unrelated, or separately unauthorized path or
  action changed.

Verify idempotence by reconstructing the same approved plan from the final tree
without writing and confirming that every item is already satisfied. If a
deterministic generator or dry-run mode exists, compare its proposed output with
the final files. The structural validator alone is not evidence of idempotence.

For ruleset 1, run the read-only health check and inspect its severity. When an
approved baseline and digest exist, also inspect the ratchet delta; otherwise
the check remains unbaselined advisory output. Do not auto-fix findings, copy a
generated baseline candidate into the project, refresh an existing baseline,
raise a budget, or add an exemption to make validation pass. Any such change
needs a newly displayed, separately approved migration item. Follow
[health.md](health.md) for severity and no-regression behavior.

Only after structural validation passes may a separate approved item finalize a
release-log entry as completed; re-run validation and inspect the final diff
after that write. A successful migration ends only when the actual changed-path
and hunk set exactly matches the effective approved items. Report validation
evidence in the response.

## Partial failure and recovery

On the first failed write, unexpected delta, or validation step:

1. stop further mutation;
2. re-read affected files and capture their post-failure fingerprints;
3. list every item as succeeded, failed, skipped, or not attempted;
4. preserve user or concurrent content written after the approved baseline;
5. propose for each affected file a bounded `repair`, `reverse managed delta`,
   or `leave for manual handling` action;
6. obtain item-level approval before any recovery action that changes a file;
7. revalidate and report whether the project is recovered or remains partial.

Rollback only the managed migration delta. Never use a broad reset, checkout,
restore, directory replacement, or backup copy that could erase project
knowledge, business code, or concurrent work created after migration started.
Recovery approval does not revive expired migration approval or authorize
unattempted items.

## Agent state transitions

Use these states to prevent audit, approval, and execution from blending:

| State | Allowed next state | Write authority |
|---|---|---|
| `AUDITING` | `REPORTED_NO_WRITE` or `WAITING_ITEM_DECISIONS` | none |
| `WAITING_ITEM_DECISIONS` | revised proposal, `READY_APPROVED_SUBSET`, or stop | none |
| `READY_APPROVED_SUBSET` | `EXECUTING` or revised proposal after baseline drift | approved items only |
| `EXECUTING` | `VALIDATING` or `HALTED_PARTIAL` | approved items only |
| `VALIDATING` | `COMPLETE_VALIDATED` or `HALTED_PARTIAL` | no scope expansion |
| `HALTED_PARTIAL` | `WAITING_RECOVERY_DECISIONS` | none |
| `WAITING_RECOVERY_DECISIONS` | `RECOVERING` or stop | none |
| `RECOVERING` | `COMPLETE_RECOVERED` or `STOPPED_PARTIAL` | approved recovery items only |

Never enter `EXECUTING` directly from an audit or broad migration request. Never
continue past the first failure, and never represent a partial state as
completed.
