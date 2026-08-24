# Project Memory workflows for new and existing projects

[简体中文](workflows.zh-CN.md)

This guide is for project owners and everyday users. It explains when to initialize a new project and when an existing project must be audited before migration. The enforceable agent protocols live inside the skill package; this guide explains what you should see, which decisions belong to you, and how to accept the result.

## Contents

- [Choose the correct path](#choose-the-correct-path)
- [Human and agent responsibilities](#human-and-agent-responsibilities)
- [Path A: initialize a new project](#path-a-initialize-a-new-project)
- [Path B: migrate an existing project](#path-b-migrate-an-existing-project)
- [Upgrade a project created by an older version](#upgrade-a-project-created-by-an-older-version)
- [Codex and Claude Code](#codex-and-claude-code)
- [Definition of done](#definition-of-done)

## Choose the correct path

| Project condition | Path | Write rule |
|---|---|---|
| A new directory, or a long-lived project with no coherent project memory | Initialize | The agent performs a read-only preflight. If the root is clear and the project is genuinely new, it may carry out the explicitly requested minimal initialization. |
| Existing requirements, plans, ADRs, handoff state, experience, an equivalent Project Memory rule in `AGENTS.md` or `CLAUDE.md`, or an older Project Memory setup | Existing-project migration | The agent must finish a zero-write audit, show a file-level proposal, and obtain approval for the exact scope before writing. |
| It is unclear whether existing documents already own project-memory roles | Existing-project migration | Use the conservative migration path and classify documents by content, not filename. |

Installing or updating the skill never changes a project automatically. Audit and approve each existing project separately.

## Human and agent responsibilities

The project owner should:

- identify the intended project root;
- decide matters that materially affect scope, conventions, authority, or compatibility;
- review the proposed files, actions, risks, and recovery basis;
- approve, modify, reject, or defer migration items individually;
- inspect the final diff and validation evidence, then decide whether a failed item should be repaired or rolled back.

The agent must:

- identify the root, existing documents, host entry files, and path boundaries before any write;
- classify canonical documents by content and references rather than filenames;
- preserve existing content and conventions instead of creating competing copies to match a template;
- distinguish verified facts, user decisions, assumptions, and unresolved items;
- perform only currently authorized actions inside the selected project;
- keep the migration audit stage strictly zero-write;
- apply only approved file-level changes and report the actual diff, validation, and recovery path.

## Path A: initialize a new project

### 1. Request initialization

Recommended prompt:

```text
Use Project Memory to initialize durable project memory in the current directory. Start with a read-only preflight. If you find existing project memory, requirements, ADRs, handoff records, or equivalent entry instructions, switch to an existing-project migration audit and stop before writing. If this is genuinely a new project, create only the minimum files with real content, then report the diff and validation evidence.
```

This authorizes only minimal initialization inside the selected project. It does not authorize scanning other projects, installing or updating the skill, committing or pushing Git changes, publishing, or taking external actions.

### 2. The agent performs a read-only preflight

The preflight identifies at least:

- the normalized project and repository roots;
- Codex, Claude Code, or shared-host entry points;
- existing `.planning/`, requirements, roadmaps, ADRs, state, experience, and equivalent instructions;
- out-of-root symlinks, concurrent writers, and ambiguous canonical documents;
- the main documentation language.

If equivalent material already exists, the agent must stop treating the project as empty and use the migration workflow below.

### 3. Create the minimum useful structure

The default initialization creates only:

- `.planning/context.md` for stable intent, constraints, high-level state, the real index, and schema;
- `.planning/release-log.md` for meaningful newest-first history;
- one concise managed entry block for each applicable host, written last.

Create `state.md`, retrospectives, glossary, decision, experience, template, and topic records only after real content needs them. Do not generate empty shells.

### 4. Ask only material questions

If the root, host, existing convention, or scope is materially ambiguous, the agent should provide a recommendation and consequence before asking. A clear, reversible, explicitly requested initialization does not need a second ceremonial approval.

### 5. Accept the initialization

Confirm that:

- every created file contains real content;
- no existing project material was overwritten;
- shared-host `AGENTS.md` and `CLAUDE.md` point to the same memory;
- the index lists only files that exist;
- the validator passes and the final diff matches the report;
- the agent explains how to resume project work later.

## Path B: migrate an existing project

Migration has four fixed stages. Stages 1 and 2 are read-only. The agent cannot enter stage 3 without explicit approval.

### Stage 1: read-only audit

Recommended prompt:

```text
Use Project Memory to perform a pre-migration audit of this project. During the audit, do not create, modify, delete, move, or rename any file. Report the audited root, baseline, schema classification, canonical-role mapping, conflicts and stale content, unsafe paths, minimal migration items, recovery basis, and validation plan. Then stop for my item-by-item decision.
```

The audit report should contain:

- root, date, and an identifiable Git or file baseline;
- a proposal ID and revision so approval cannot drift to a later plan;
- classification as `schema 1`, `legacy managed`, `partial`, `foreign convention`, or `ambiguous`;
- each path's observed role, evidence, freshness, owner or convention, and conflicts;
- out-of-root symlinks, concurrent writers, and unresolved authority;
- numbered items such as `MIG-01` and `MIG-02`;
- target files, minimal actions, preserved content, risks, and expected diff for each item;
- recovery basis and post-migration validation;
- an explicit statement that the audit completed with zero writes.

Keep the audit report in the conversation. Writing an audit file into the project would violate the zero-write stage.

### Stage 2: decide item by item

Approval must refer to specific items in the current audit. For example:

```text
Approve MIG-01 and MIG-03 from plan PM-MIG-2026-08-24 revision 1 exactly as proposed. Do not apply MIG-02 or change any other file.
```

To modify a proposal:

```text
For plan PM-MIG-2026-08-24 revision 1, approve MIG-01. Modify MIG-02 so docs/adr/ remains the canonical path and no .planning/decisions/ directory is created. Show a new revision and wait for confirmation of the modified item.
```

Silence, continued conversation, installing a new skill version, or a broad request to “use Project Memory” or “upgrade the project” is not migration approval. Deleting or moving files, accessing paths outside the root, committing or pushing Git changes, publishing, and changing global installations require their own authorization.

If an item is modified, its new revision returns to pending. Partial approval is executable only when every dependency and every member of an indivisible execution group is approved, and the subset still leaves a structurally valid project. Otherwise, the agent must write nothing and explain the minimum additional decision needed. If the baseline changes before execution, affected approval items expire and the agent must re-read and re-propose them.

### Stage 3: execute the approved migration

The agent may touch only approved files and actions. It should:

1. re-read every target immediately before writing;
2. verify the pre-existing read-only baseline and prepare each approved item's
   file-specific reverse delta; create no backup or Git commit unless it is a
   separately listed and approved item;
3. add or update canonical records with the smallest diff;
4. preserve attribution and unique history, marking uncertain material `待确认`;
5. update the real index and keep release-log status accurate without claiming
   completion before validation;
6. write managed host entry blocks last, after every referenced file exists;
7. re-read every changed file.

Migration is not permission to format, rename, or clean unrelated files.

### Stage 4: validate and recover

The agent runs the read-only validator and inspects the actual diff. It verifies at least:

- every path and resolved symlink remains inside the project root;
- context and managed-marker schemas agree;
- indexes and Markdown links resolve;
- IDs are unique and active handoff state has an exact next action;
- unique original content and concurrent changes remain present;
- a second dry run of the same approved plan would produce no diff;
- actual changes do not exceed approved items.

At the first failed write or validation step, the agent stops, lists succeeded, failed, and unattempted items, and proposes a file-specific repair or reverse patch. A rollback that changes files also requires approval. Never use a broad reset or restore that could erase work created after migration began.

Only after structural validation passes may an approved release-log item be
finalized as completed; the agent then validates and inspects the final diff
again.

## Upgrade a project created by an older version

Update the plugin or standalone skill first, then run the existing-project workflow separately in every project. A version update does not imply that the project schema must change. Only a schema change or an explicitly chosen project improvement needs migration.

Do not copy a new `.planning/` directory over the old one. Existing `CONTEXT.md`, `STATE.md`, `docs/adr/`, changelog, or experience libraries may remain canonical and be indexed by the new protocol.

## Codex and Claude Code

Both hosts share one project memory:

- Codex uses the applicable `AGENTS.md`;
- Claude Code uses the applicable `CLAUDE.md`;
- a shared project points both entry files to the same `.planning/context.md`;
- neither entry file should duplicate the full memory.

## Definition of done

The workflow is complete only when:

- the project was classified into the correct path;
- an existing-project migration has a demonstrably zero-write audit stage;
- every actual change maps to explicit initialization authority or an approved migration item;
- existing content, canonical conventions, and concurrent changes remain intact;
- the validator and project-specific checks pass, or failures are reported accurately;
- the final report names the root, changed files, preserved mappings, validation evidence, recovery path, and highest-priority unresolved decision.
