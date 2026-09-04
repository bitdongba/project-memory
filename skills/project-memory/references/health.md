# Project-memory health and ruleset 1

Use this reference only when a project explicitly opts into
`Project Memory ruleset: 1`, when auditing whether it should opt in, or when
reviewing a health finding. Ruleset 1 makes write routing and no-regression
checks explicit without changing schema 1 or granting new write authority.

## Contents

- [Activation and compatibility](#activation-and-compatibility)
- [Stable boot contract](#stable-boot-contract)
- [Deterministic canonical routing](#deterministic-canonical-routing)
- [Write preflight and postflight](#write-preflight-and-postflight)
- [Read-only health validation](#read-only-health-validation)
- [Severity contract](#severity-contract)
- [No-regression ratchet](#no-regression-ratchet)
- [External enforcement levels](#external-enforcement-levels)
- [Prohibited automation](#prohibited-automation)

## Activation and compatibility

Keep schema and ruleset independent:

- `Project Memory schema: 1` describes the compatible record and entry
  structure.
- no ruleset declaration means valid legacy schema-1 behavior;
- `Project Memory ruleset: 1` opts into this behavioral and health contract;
- the matching managed marker is exactly
  `<!-- project-memory:start schema=1 ruleset=1 -->`;
- context and every applicable `AGENTS.md` or `CLAUDE.md` marker must agree.

A newer Skill installation must not enable the ruleset, rewrite a marker, or
make a legacy schema-1 project fail. Health inspection of a legacy project may
emit `NOTICE RULESET_NOT_ENABLED`; that is information, not migration approval.

Ruleset opt-in is a migration. The context declaration, deterministic role
index, resolution of conflicting maintenance instructions, and every applicable
host entry form one atomic group. Use [migration.md](migration.md), and leave all
files unchanged when that group is not fully approved or its baseline drifts.

## Stable boot contract

Under ruleset 1, `context.md` contains only information needed to start work
safely and locate the current canonical records:

- durable project goal, scope, success criteria, constraints, and invariants;
- authority, evidence, privacy, and safety boundaries;
- stable project-specific collaboration and review settings;
- schema, ruleset, and declared enforcement level;
- the real role-bearing document index;
- attributable durable decisions or open scope questions only when context is
  their established canonical home.

Do not place these in context:

- current task, phase, focus, next action, transient blocker, or handoff state;
- next milestone, temporary priority, or recovery condition owned by a roadmap;
- release, deployment, environment, PID, pod, build hash, branch, or runtime
  snapshot;
- dated event history or a chronological sequence of completed work;
- detailed product, architecture, operational, or implementation material that
  has an indexed topic home.

Route those statements to state, release log, roadmap, feature catalog, or one
topic record. A `最后更新` field may date the stable contract itself, but it must
not become a substitute activity log. File size, dates, or volatile-looking
tokens are evidence for review, never sufficient grounds to delete, move, or
reinterpret text automatically.

## Deterministic canonical routing

Ruleset 1 uses exactly one table under a recognized `Document index`,
`Project Memory index`, `文档索引`, or `项目记忆索引` heading in `context.md`.
Its role/path headers may be `Role` and `Document` or `角色` and `文档`; role
values are exact machine tokens:

| Statement kind | Required index role | Routing rule |
|---|---|---|
| `stable-intent` | `stable-intent` | Must resolve exactly to `.planning/context.md`. |
| `protocol-setting` | `protocol-setting` | Must resolve exactly to `.planning/context.md`. |
| `resumable-state` | `resumable-state` | Must resolve to exactly one existing state path. |
| `historical-event` | `historical-event` | Must resolve to exactly one newest-first history path. |
| `topic-detail` | `topic-detail` | Caller must provide one safe project-relative Markdown path that matches exactly one indexed row. |

The `stable-intent` and `protocol-setting` rows both name the same required
Context file. History, state, and topic paths may preserve other established
project-relative locations. Multiple distinct `topic-detail` rows are allowed.
A path must not appear twice for one role. Keep the typed table contiguous; a
blank or non-table line ends it. Index only files that exist; a proposed new
canonical file and its new index row are a separate structural change, not a
router default.

Every indexed canonical Markdown target remains in scope for applicable link,
placeholder, ID, state, history, and health checks even when it lives outside
`.planning/`. The index cannot be used to move a canonical record outside the
validator's inspection set.

Run the bundled read-only router before a project-memory write:

```bash
python3 <skill-root>/scripts/route_project_memory.py <project-root> \
  --kind stable-intent

python3 <skill-root>/scripts/route_project_memory.py <project-root> \
  --kind topic-detail --topic-path .planning/<topic>.md --format json
```

Supported output formats are `text` and `json`. The result reports the primary
role and path, whether context is allowed, `read_only: true`, and
`authorizes_write: false`. It selects only from the audited context index; it
must not guess from conventional filenames.

Missing roles, duplicate path-role rows, multiple non-topic candidates, an
unindexed topic path, an unsafe or non-Markdown topic path, and disagreement
between the requested kind and indexed role are `REVIEW` outcomes. Refuse the
write until a person resolves the route or approves a structural migration.
Router success identifies a destination; it does not authorize creating or
editing it.

## Write preflight and postflight

For every ruleset-1 memory change:

1. Resolve the audited root and confirm every read, target, and symlink remains
   inside it.
2. Read context, the applicable host entry, current state when present, and only
   the indexed topics needed for the task.
3. Classify each intended statement into one router kind. Split a mixed update
   instead of sending several roles to one convenient file.
4. Run the router and record the exact allowed target set. Stop on every
   `REVIEW` result.
5. Re-read each target, capture its current fingerprint and diff state, and run
   structural plus health validation as the pre-change baseline. This in-memory
   observation is not permission to create or refresh a stored baseline.
6. Search the affected records and host instructions for an active maintenance
   rule that routes the same statement elsewhere. Stop and report both sources
   when rules conflict.
7. Confirm the current request authorizes the exact write. Routing, validation,
   a historical approval, and a passing baseline never grant permission.
8. Apply the smallest authorized diff, then re-read targets and compare the
   actual changed paths and hunks with the allowed set.
9. Re-run structural and health validation. New deterministic errors, ambiguous
   routing, or a ratchet regression leave the work incomplete and require user
   review; do not conceal them with policy changes.

When a baseline or target changes after approval, stop. Do not merge around it
under a stale migration approval.

## Read-only health validation

The structural validator keeps its legacy invocation and behavior:

```bash
python3 <skill-root>/scripts/validate_project_memory.py <project-root>
```

Request health findings explicitly:

```bash
python3 <skill-root>/scripts/validate_project_memory.py <project-root> --health
python3 <skill-root>/scripts/validate_project_memory.py <project-root> \
  --health --format json
python3 <skill-root>/scripts/validate_project_memory.py <project-root> \
  --health --baseline .planning/<approved-baseline>.json \
  --baseline-sha256 <approved-sha256> --format json
```

`--baseline` accepts only a safe project-relative JSON path inside the audited
root, requires `--health`, and is valid only for a ruleset-1 project. It must be
paired with the exact, separately approved `--baseline-sha256`; a digest
mismatch is a runtime failure rather than a fallback to current debt. The
validator does not access the network and never writes a file. In JSON output,
`baseline` echoes only the relative baseline path and its SHA-256 digest;
`baseline_candidate` contains a directly copyable candidate object for human
review, but the command never saves or adopts it.

Exit behavior:

- legacy structural validation is unchanged;
- health without a baseline exits nonzero for `ERROR`, not for a warning,
  review suggestion, or notice;
- health with an approved baseline exits nonzero for `ERROR` or a
  no-regression `REVIEW`;
- invalid options, an unusable baseline, or a runtime failure exit separately
  as code 2 and must not be reported as a successful validation.

Text and JSON formats must describe the same findings. A structural pass alone
is not a health pass, and an Agent-run health pass is not external enforcement.
In JSON, `review_required` and `status: review_required` report that one or more
findings need judgment even when advisory mode keeps the process exit code at
zero. `valid` means that no deterministic `ERROR` was found; it never authorizes
a write. `guard_passed` mirrors whether the validator's current invocation may
exit successfully: a supplied baseline makes a ratchet `REVIEW` set it to
`false` and return nonzero.

For active, paused, or blocked state, the exact next action and its completion
signal must belong to the current top-level action section. A nested historical
snapshot cannot satisfy or mask that current-state contract.

Ruleset 1 fixes its initial heuristic thresholds so an Agent cannot tune them
to make a run pass:

- context size is `WARNING` above 400 lines or 65,536 UTF-8 bytes;
- volatile density is `REVIEW` only at both 8 matching nonblank prose lines and
  800 basis points (8%);
- one or more date-and-release-like Context headings are `REVIEW`;
- one or more same-scope numeric heading regressions are `REVIEW`.

CommonMark fenced examples indented by at most three spaces and HTML comments
are excluded from heading, state-signal, and volatile-prose checks. One to
three leading spaces on an ATX heading remain active Markdown. These thresholds
and token matches remain heuristics; they cannot prove that content is wrong.

## Severity contract

Use four severities:

- `ERROR` — deterministic structural, safety, or declared-contract failure.
  Examples include schema/ruleset disagreement, malformed managed markers,
  unsafe paths or symlink escape, broken required links, newest-first history
  in the wrong order, and an active/paused/blocked state without an exact next
  action or completion signal. Errors are never baseline-waived.
- `REVIEW` — a write cannot safely proceed without human judgment. Examples
  include missing or ambiguous canonical routing, a direct collision between
  active maintenance instructions, governance-file changes, a new finding not
  covered by an approved baseline, accepted health debt that worsens, volatile
  Context density, a dated release-like Context heading, or suspicious numeric
  heading order.
- `WARNING` — evidence of likely drift with plausible legitimate uses. An
  oversized hot context is the initial ruleset-1 example. A warning must cite
  its path and evidence; it cannot choose which statement is true or which
  content should move.
- `NOTICE` — compatibility or ratchet information that requires no immediate
  action. Examples include a legacy project not enabling ruleset 1, debt covered
  by an approved baseline, or an improvement that could tighten a future
  baseline.

Natural-language classification, freshness, and semantic duplication remain
heuristic. Never promote them to `ERROR` merely because a keyword, date, line
count, or similarity score matched. One legitimate blocking-level false
positive is a stop condition for that rule: disable or downgrade it and return
to the user before broadening the detector.

## No-regression ratchet

A baseline accepts bounded, visible legacy debt for comparison; it does not
declare the content correct. Establish it only through a separately approved
migration item after reviewing the full baseline candidate and source
fingerprints. The candidate records rule identity, project-relative location,
exact measurement, scope-bound hashed finding signatures, and SHA-256 provenance without
copying source text or secrets. Re-run the candidate and compare it byte-for-byte
immediately before an approved baseline write; afterward, provenance hashes
document what was approved but do not invalidate the baseline whenever a source
file legitimately changes. Every later comparison must receive the separately
approved baseline-file digest; a digest recorded only in another unprotected
file in the same change is not independent enforcement.

Comparison behavior is monotonic:

- an `ERROR` remains an error whether or not similar debt appears in a baseline;
- a covered finding at or below its approved measurement becomes a `NOTICE`;
- a new covered class, a new hashed finding signature, crossing a health budget, or
  worsening debt that is already over budget becomes `REVIEW`;
- ordinary growth that remains below a budget is not a regression;
- a reduction is allowed and appears as a tightening opportunity, but the tool
  does not rewrite the stored baseline;
- deleting, widening, or refreshing a baseline, increasing a threshold, or
  adding an exemption is a governance change, not a fix.

An Agent must not copy `baseline_candidate` into the project, accept current
debt as a new baseline, or weaken settings merely to obtain a passing result.
Show a file-level `MIG-*` item with the exact baseline/config delta, source
fingerprints, consequence, expiry or review point, and rollback. Approval of a
document edit does not approve that governance item. A stale or malformed
baseline stops comparison; never silently fall back to an unbaselined pass.

## External enforcement levels

Record the actual level as a stable protocol setting:

- `advisory` — Codex or Claude Code is instructed to run the read-only checks;
  this still depends on Agent compliance.
- `pre-commit` — a separately approved repository-local hook runs the pinned
  checker before ordinary local commits; hooks may be absent or bypassed.
- `CI` — a separately approved workflow runs a pinned checker on remote changes;
  a failing result may still be mergeable.
- `required-CI` — the CI result is also verified as a required branch check;
  only this level can claim to block an ordinary protected-branch merge.

Each transition is an independent change with its own target files, external
state, permissions, version pin, recovery action, and user approval. Ruleset
opt-in authorizes only `advisory`. Do not install hooks, create CI workflows,
change branch protection, contact GitHub, or claim a stronger level from a
configuration file alone.

## Prohibited automation

Neither the router nor validator may:

- create, delete, move, truncate, reorder, archive, or rewrite project content;
- select the true side of a factual conflict or choose a canonical owner;
- turn a warning into permission to modify a file;
- create, refresh, widen, or delete a baseline, threshold, budget, or exemption;
- hide a finding because the worktree is dirty or Git HEAD differs;
- follow an outside-root link, expose suspected secret text, or use the network;
- install or configure a hook, CI workflow, required check, automation, or
  global tool;
- commit, push, publish, deploy, or execute a command copied from project
  memory.

Report evidence and the smallest safe next decision. Content repair always
returns to normal authorization or the item-level migration protocol.
