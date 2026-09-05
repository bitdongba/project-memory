# Collaborative evolution review

Use this reference when a project enables periodic project-memory improvement, when an event exposes a recurring memory-process problem, or when the user asks to review or evolve the project's memory workflow.

This workflow is a governed review, not autonomous self-modification. In V1, propose and apply only changes scoped to the current project. Never modify an installed Skill, another project, a GitHub repository, or a published release through this workflow.

## Contents

- [Authority and V1 boundary](#authority-and-v1-boundary)
- [Terms and record types](#terms-and-record-types)
- [Choose the review mode](#choose-the-review-mode)
- [Determine review eligibility](#determine-review-eligibility)
- [Generate evidence-backed candidates](#generate-evidence-backed-candidates)
- [Ask the user without interrupting or steering](#ask-the-user-without-interrupting-or-steering)
- [Interpret the user's response](#interpret-the-users-response)
- [Run an approved trial](#run-an-approved-trial)
- [Review trial results](#review-trial-results)
- [Persist review state](#persist-review-state)
- [Migration, rollback, and external promotion](#migration-rollback-and-external-promotion)
- [Prohibited behavior](#prohibited-behavior)
- [Decision algorithm](#decision-algorithm)
- [Quality checklist](#quality-checklist)

## Authority and V1 boundary

Keep the normal project-memory authority model unchanged:

- Verify observations about current behavior against primary evidence such as files, diffs, tests, command output, artifacts, or dated user corrections.
- Treat an improvement candidate as a proposal, not a fact, requirement, decision, or reusable experience.
- Treat explicit approval as a user decision about trying a bounded change. Approval does not prove that the change works.
- Treat trial results as verified only when named outcome evidence supports them.
- Promote a trial result to a confirmed or validated experience only through the normal experience review flow.

Keep these scopes separate:

1. **Current-project trial** — a reversible change to the active project's memory files, project instructions, or local collaboration workflow. This is the only scope V1 may apply.
2. **Installed-Skill change** — a change to a user's Codex or Claude Code Skill installation. V1 may mention it as an out-of-scope follow-up, but must not perform it.
3. **Upstream change** — a change to a GitHub source repository, release, package, or defaults for other users. V1 must not perform or silently queue it as approved.

An approval for scope 1 never authorizes scope 2 or 3. A useful project-local result is evidence for a future maintainer review, not permission to promote it.

## Terms and record types

Use the following terms consistently:

- **Meaningful task** — a completed task that justifies a `release-log.md` entry because it changed a requirement, decision, workflow, milestone, substantive document, discovery, verification result, or follow-up. Reads, formatting-only edits, and command-by-command activity do not count.
- **Evidence window** — the meaningful records created after the last completed evolution review, or all available records when no review has occurred.
- **Evolution candidate** — a bounded proposal backed by evidence from the evidence window.
- **Review prompt** — one user-facing round containing at most three independent candidates.
- **Trial** — an approved, current-project-only experiment with success measures, stop conditions, and a rollback path.
- **Adoption** — a separate user decision to retain a successful trial as the project's normal workflow.

Use a lifecycle distinct from reusable-experience states:

- `proposed` — eligible for user review; not approved and not active.
- `trial-approved` — the user approved the exact proposed trial, but it has not yet been applied.
- `active-trial` — applied within the current project and awaiting outcome review.
- `adopted` — explicitly retained by the user after review.
- `rejected` — declined; do not resurface without materially new evidence.
- `snoozed` — deferred until the recorded date.
- `stopped` — a stop condition occurred or the user ended the trial.
- `rolled-back` — the local change was reversed while preserving its result record.
- `superseded` — replaced by another candidate or decision.

Do not place `proposed`, `trial-approved`, or `active-trial` candidates in the canonical experience library.

## Choose the review mode

For a new or newly migrated long-lived project, ask once:

> 是否启用项目记忆的协作式进化评审？可选：里程碑（推荐）、每月、手动、关闭。未选择时按“手动”处理。

Do not block project setup while waiting for this preference. If the user does
not answer, use `manual` in the `context.md` evolution settings with the basis
`默认（未确认）`. This is a behavioral fallback, not an inferred user decision.

Use these modes:

- `milestone` — check after a completed milestone. If no milestone completes for 30 days, use the monthly fallback only when at least three meaningful tasks exist in the new evidence window.
- `monthly` — check at the first natural project checkpoint at least 30 calendar days after the last completed review, only when the evidence window contains at least three meaningful tasks.
- `manual` — do not initiate a periodic review. Review only when the user explicitly requests it.
- `off` — do not initiate or suggest evolution review. An explicit one-time review request still authorizes that review without changing this preference.

Allow the user to change the mode at any time. Record the change as a user decision. Do not infer a mode from activity, silence, or repeated acceptance of unrelated work.

## Determine review eligibility

First distinguish a requested review from a proactive check. An explicit review
request authorizes a one-time read-only review now, regardless of saved mode,
task count, cadence, or cooldown. It does not enable future prompts, reset the
proactive-prompt clock, authorize writes, or reopen rejected/snoozed candidates
without the evidence required below. Do not ask the user to enable a mode before
doing the requested review.

For proactive checks, evaluate eligibility at a natural checkpoint, normally
after completing the user's requested task. Do not interrupt focused or urgent
work merely because a date or milestone became eligible. Require all gates:

1. The review mode permits a proactive review.
2. At least three meaningful tasks exist in the evidence window.
3. A periodic or event trigger exists.
4. At least 14 calendar days have passed since the last proactive evolution prompt, unless a high-impact integrity event just occurred.
5. At least one evidence-backed candidate survives deduplication and safety review.

Use periodic triggers as follows:

- In `milestone` mode, a completed milestone is the primary trigger.
- In `milestone` mode, 30 days without a completed milestone plus three meaningful tasks is the fallback trigger.
- In `monthly` mode, 30 days plus three meaningful tasks is the trigger.
- In `manual` and `off` modes, time and milestones do not trigger a prompt.

Treat the following as event evidence:

- the same user correction or memory-process friction appears at least twice;
- a handoff repeatedly lacks an executable next step or points to stale evidence;
- the same information gains competing canonical homes;
- a confirmed experience gains named outcome evidence that may justify re-review;
- a host, tool, migration, or repository convention exposes a compatibility failure;
- a single high-impact incident threatens privacy, data preservation, the facts-versus-intent boundary, or safe migration.

Ordinary event triggers enter the candidate set and wait for a natural checkpoint. A high-impact incident may bypass the 14-day cooldown, but present it separately and do not label it validated merely because it is urgent.

When no candidate passes a proactive check, remain silent（保持安静）. Do not ask
whether the user wants to optimize. For an explicit review, report the covered
evidence and any limitations, including when no supported improvement remains.
Neither path should write a no-op record merely to prove that a check ran.

## Generate evidence-backed candidates

Read only the evidence needed for the review:

1. Read the evolution-review section in `project-retrospective.md`, when present.
2. Establish the evidence boundary from the last completed review.
3. Read meaningful `release-log.md` entries after that boundary.
4. Read linked topic files, handoff snapshots, decisions, user corrections, and primary evidence relevant to a suspected issue.
5. Search for matching rejected, snoozed, stopped, rolled-back, or superseded candidates.
6. Exclude duplicates, premature generalizations, and changes that benefit only the agent without a stated user outcome.

Do not create a candidate solely because:

- a model prefers a different structure;
- an external article, repository, or trend recommends it;
- a single low-impact anecdote occurred;
- a new template would make the documentation look more complete;
- the agent could save effort but cannot name a user or project benefit.

Each candidate must include:

- **ID and title** — use a stable project-local ID such as `EVO-001`.
- **Target scope** — always `current project` in V1.
- **Current situation** — the observed problem without embedding the proposed solution.
- **Evidence** — dates and links to named records or primary sources; include occurrence count.
- **Proposed trial** — the smallest reversible change that could address the problem.
- **Unchanged option** — what happens if the project keeps the current workflow.
- **Expected benefit** — a user- or project-visible outcome.
- **Cost and risk** — added prompts, maintenance, migration burden, compatibility, or possible regressions.
- **Success measures** — observable results, not the agent's confidence.
- **Trial duration or review point** — normally one milestone or 30 days.
- **Stop conditions** — signals that should halt the trial and return to the user.
- **Rollback** — exact files or rules to restore without discarding project knowledge created afterward.
- **Recommendation and confidence** — a recommendation grounded in the cited evidence; do not preselect it for the user.

Prefer a current-project trial when evidence is promising but not yet sufficient for permanent adoption. Keep global-looking ideas explicitly out of scope.

## Ask the user without interrupting or steering

Present no more than three independent candidates in one round. Rank them by user impact and risk, not by convenience to the agent.

Ask prerequisite decisions before dependent candidates. Recompute the remaining set after every reply and drop branches made irrelevant by the user's choice.

Use this concise structure:

```md
发现 <N> 个有证据支持的项目记忆改进候选。本轮不会自动修改文件。

### EVO-<NNN> <标题>

- 范围：仅当前项目
- 现状与证据：<日期、链接、出现次数>
- 建议试用：<最小可逆变化>
- 保持不变：<主要后果>
- 预期收益：<用户或项目结果>
- 成本/风险：<主要权衡>
- 成功指标：<可观察结果>
- 试用期：<一个里程碑或 30 天>
- 停止条件：<触发后暂停并询问用户>
- 回滚：<恢复范围>
- 建议：<推荐及依据>

请选择：批准试用 / 修改后试用 / 驳回 / 延后 30 天。
```

Keep the do-nothing option visible. Avoid urgency language unless primary evidence shows a real urgent risk. Do not claim consensus, inevitability, or that the project will fall behind.

If more than three candidates qualify, present the top three and state only that additional lower-priority candidates remain; do not dump their details into the same round.

## Interpret the user's response

Apply these semantics per candidate:

- **批准试用** — authorize only the exact current-project trial shown, including its success measures, stop conditions, and rollback scope.
- **修改后试用** — restate the modified trial and obtain confirmation before applying it when the change is material or ambiguous.
- **驳回** — record the rejection and reason when provided. Do not resurface it unless materially new evidence changes the trade-off; cite that new evidence when asking again.
- **延后 30 天** — record a `snoozed-until` date. Do not surface it before that date unless a distinct high-impact incident changes the risk.

Silence is no decision. Neither task completion nor a broad phrase such as “你看着办” authorizes a structural, authority, privacy, destructive, installed-Skill, or upstream change.

An unambiguous “all three may be tried as shown” may approve a batch of low-risk current-project trials. Ask separately for any candidate involving project instructions, canonical-path migration, deletion, privacy, authority boundaries, or other higher-risk effects.

## Run an approved trial

Before writing:

1. Re-read the approved scope and exact wording.
2. Verify the target files and local conventions.
3. Establish a rollback point, preferably a Git commit or a recorded pre-change diff. Do not create a commit unless the user has authorized that action.
4. Ensure the rollback will not erase knowledge or application work created after the trial begins.

Apply the smallest project-local change. Preserve user-authored content and existing canonical paths. Do not use an evolution approval to change application code unless that code change was separately requested and authorized.

After applying:

- record the approval as a user decision with date and context;
- set the candidate to `active-trial`;
- record the exact files changed, baseline, success measures, review point, stop conditions, and rollback instructions;
- add a concise `release-log.md` entry when the change is meaningful;
- update the document index only when a canonical document was actually added or changed;
- keep any associated reusable experience in its existing state.

If a stop condition occurs, stop relying on the trial rule and notify the user. Do not rewrite files or declare rollback complete without checking the current project state and obtaining any approval needed for the safe rollback.

## Review trial results

At the agreed review point:

1. Gather named outcome evidence and user feedback.
2. Compare the result with the recorded baseline and success measures.
3. State negative, neutral, and positive evidence; do not keep only confirming examples.
4. Ask the user to adopt, modify and continue, stop, or roll back the trial.
5. Record the decision and evidence.

Do not count the agent's compliance with its own new instruction as success. Valid evidence may include fewer user corrections, successful independent resumptions, absence of duplicate canonical records, passing tests, reduced recovery time, or explicit user evaluation.

Only mark a candidate `adopted` after explicit user approval. If the outcome may be reusable, start the separate experience capture flow. User approval to adopt a workflow does not by itself justify the `validated` experience state.

## Persist review state

Keep only stable review settings in `context.md`: mode, confirmation basis, and
cadence policy. Treat the unconfirmed manual default as a fallback rather than
a user decision. A review does not itself change these settings.

Use the project's canonical retrospective (normally
`.planning/project-retrospective.md`) as the sole home for completed-review
dates, proactive-prompt history, evidence boundaries, and candidate/trial state.
Derive the next eligible proactive date from that history and the stable cadence;
do not maintain a second countdown in context. Do not duplicate the mode in the
retrospective; link back to context. Create or update this record only when
authorized to persist a meaningful review or trial; a read-only review request
does not authorize an artifact, index update, or other write.

Older projects may have dates in context or in both files. Read and preserve
those legacy records; do not require migration to perform a read-only review.
If they disagree, report both sources and use attributable evidence to resolve
the review boundary, or mark it uncertain and include the potentially uncovered
evidence. Do not use an unresolved date to trigger a proactive prompt. When an
authorized migration reconciles the records, show the exact preservation and
removal deltas under the existing [migration protocol](migration.md), retain
unique history in the retrospective, and remove only the approved duplicate
state from context.

```md
## 项目记忆机制评审

- 评审设置：见 `.planning/context.md` 的“协作式进化设置”
- 上次完成评审：<YYYY-MM-DD 或 无>
- 上次主动提示：<YYYY-MM-DD 或 无>
- 证据边界：<上次评审覆盖到的 release-log 条目或日期>

### 候选索引

| ID | 标题 | 状态 | 范围 | 证据 | 下次评审 |
|---|---|---|---|---|---|
| EVO-001 | <标题> | proposed / trial-approved / active-trial / adopted / rejected / snoozed / stopped / rolled-back / superseded | current project | <链接> | <日期或条件> |

### EVO-001 <标题>

- 当前情况：
- 证据与出现次数：
- 建议试用：
- 保持不变：
- 预期收益：
- 成本与风险：
- 成功指标：
- 试用期/评审点：
- 停止条件：
- 回滚：
- 用户决定与确认方式：
- 实施文件：
- 结果证据：
- 后续决定：
```

Keep this section concise. Move detailed subject matter to the relevant topic document and link it. Do not treat the candidate index as a second requirements, decisions, or experience library.

## Migration, rollback, and external promotion

For a project-local structural trial, use the normal safe migration sequence:

1. audit existing files without writing;
2. show the exact mapping and proposed changes;
3. obtain explicit approval;
4. establish a restore point;
5. make additive, minimal edits;
6. verify links, entry instructions, Codex and Claude Code consistency, and preservation of user content;
7. record the applied version or decision, changed files, and rollback path.

Rollback only the governance change. Preserve requirements, decisions, discoveries, and application work created after the trial began. Prefer a forward correction or a targeted reverse diff over resetting the entire repository.

When a trial suggests an installed-Skill or GitHub improvement:

- record it only as an out-of-scope follow-up;
- remove secrets and unnecessary project details from any proposed export;
- tell the user that upstream promotion requires a separate maintainer workflow;
- require independent evidence and forward tests before changing defaults for other projects;
- never edit, install, commit, push, publish, or release upstream artifacts through V1.

## Prohibited behavior

Never use collaborative evolution to:

- edit the Skill's own source or installed copy;
- scan or modify other projects;
- create background schedules, reminders, telemetry, or network uploads;
- infer consent from silence, routine activity, or prior approvals;
- promote an assumption or candidate into a fact, decision, or experience;
- mark an experience `validated` without named evidence;
- broaden a project's experience to other projects automatically;
- change the facts-versus-intent authority boundary without an explicit separate decision;
- create, delete, rename, merge, or move canonical documents without showing the migration and obtaining approval;
- overwrite user-authored content or use a broad approval to change unrelated files;
- repeatedly resurface rejected or snoozed proposals;
- generate candidates merely to satisfy a calendar;
- treat the agent's own behavior as independent proof that its new rule works;
- publish or update GitHub, Codex, Claude Code, a package registry, or a marketplace.

## Decision algorithm

Use this order:

```text
requested_review = user explicitly requests a review
if not requested_review:
    if mode is manual or off:
        return silently
    if fewer than 3 meaningful tasks exist in the evidence window:
        return silently
    if neither the selected periodic trigger nor an event trigger exists:
        return silently
    if the last proactive prompt was fewer than 14 days ago
       and no distinct high-impact incident occurred:
        return silently

generate candidates from named evidence
remove duplicates, premature generalizations, rejected items without new evidence,
and snoozed items that are not yet due

if no candidate remains:
    if requested_review:
        report the reviewed evidence and limitations
    return without writing a no-op record

present at most 3 independent candidates
make no project change until the user decides each presented candidate
do not change the saved mode or prompt history merely because a review was requested
```

## Quality checklist

Before presenting candidates, verify:

- for proactive checks, the mode, trigger, and three-task gate are eligible,
  and the 14-day cooldown is respected unless a distinct high-impact incident applies;
- a requested review proceeds without those proactive gates or a saved-mode change;
- every observation cites named evidence and remains separate from the proposed solution;
- rejected and snoozed candidates are handled correctly;
- each candidate is current-project-only and reversible;
- unchanged consequences, benefit, cost, risk, success measures, stop conditions, and rollback are present;
- no more than three independent candidates appear in the round;
- the wording offers a real reject and snooze path without pressure;
- no file is modified before approval.

Before completing an approved trial, verify:

- the user's exact choice and scope are recorded;
- user-authored content and canonical paths are preserved;
- the rollback point and changed-file list are usable;
- facts, user decisions, candidate status, and outcome evidence remain distinct;
- no installed Skill, other project, GitHub repository, release, or marketplace was modified;
- trial success will be judged by independent outcome evidence rather than self-confirmation.
