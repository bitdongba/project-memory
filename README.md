# Project Memory

[简体中文](README.zh-CN.md)

Project Memory is a skills-only plugin for maintaining durable, reviewable project context in Markdown. It gives Codex and Claude Code one shared `.planning/` memory for requirements, decisions, terminology, handoffs, lessons, and project history while keeping current operational facts tied to primary evidence.

Version `0.1.0` is an initial public preview.

## What it does

- Creates or migrates a project memory without replacing existing documentation wholesale.
- Separates verified facts, user decisions, assumptions, and open questions.
- Keeps stable context, current handoff state, and chronological history in different documents.
- Preserves exact constraints, including negative requirements, ordering guarantees, numerical defaults, and acceptance criteria.
- Uses focused clarification only when ambiguity materially affects scope, risk, cost, workflow, architecture, or acceptance.
- Captures reusable experience only after the user reviews each candidate.
- Supports governed evolution through evidence-backed, reversible trials in the current project; the user decides what is tried and adopted.
- Shares the same `.planning/` memory through `AGENTS.md` in Codex and `CLAUDE.md` in Claude Code.

Project Memory treats `.planning/` as the durable authority for human intent. It does not treat documentation as a substitute for code, configuration, tests, command output, data, policies, or other primary evidence.

## Safety and privacy

Project Memory has no background service, telemetry, MCP server, lifecycle hook, or automatic updater. It runs only when a host invokes the bundled skill. Any bundled validator also runs only when explicitly invoked.

The skill may read project files and write `.planning/`, `AGENTS.md`, or `CLAUDE.md`, subject to the host's sandbox and approval policy. It must not silently scan unrelated projects, modify its own source, publish changes, or update an installed copy.

Do not store secrets in project memory. Prefer repository-relative paths and redacted references. Review `.planning/` before committing it because requirements, collaboration preferences, commands, and local paths may still be sensitive even when they are not credentials. See [SECURITY.md](SECURITY.md) for reporting and data-handling guidance.

## Repository layout

```text
.
├── .codex-plugin/plugin.json
├── .claude-plugin/plugin.json
└── skills/
    └── project-memory/
        ├── SKILL.md
        ├── agents/openai.yaml
        ├── references/              # focused templates, migration, entry, and evolution rules
        └── scripts/                 # deterministic validation helpers
```

The repository root is the plugin package. `skills/project-memory/` is also the standalone skill. User documentation and release files remain at the repository root and are not copied into the standalone skill.

## Installation

Choose either plugin installation or standalone installation for a given host. Installing both can expose the same skill twice.

### Codex plugin

The recommended distribution is the native plugin package at this repository root. For local testing, ask Codex's built-in plugin creator to create a personal marketplace entry for the existing checkout. This is a marketplace operation, not a request to scaffold or rewrite the plugin:

```text
Use $plugin-creator to register the existing plugin checkout at /absolute/path/to/project-memory in my personal marketplace for local testing. Preserve the checkout and do not scaffold or overwrite the plugin.
```

Refresh Codex, install **Project Memory** from that marketplace, and start a new task. When a published repository or organization marketplace contains the plugin listing, add that marketplace and install from the `/plugins` browser:

```bash
codex plugin marketplace add <owner>/<repository>
```

The GitHub shorthand works only for a repository that contains a valid marketplace catalog; the plugin manifest alone is not such a catalog. See the official [Codex plugin documentation](https://developers.openai.com/plugins/) for marketplace and installation behavior.

### Claude Code plugin

To test a local checkout as a plugin:

```bash
claude --plugin-dir /absolute/path/to/project-memory
```

For a persistent managed installation, add the repository through a Claude Code marketplace and install its `project-memory` listing. Start a new Claude Code session after installation. See the official [Claude Code plugin documentation](https://code.claude.com/docs/en/plugins) for marketplace setup.

### Standalone skill

From the repository root, install only `skills/project-memory/`.

Codex user scope:

```bash
mkdir -p "$HOME/.agents/skills"
cp -R skills/project-memory "$HOME/.agents/skills/"
```

`$HOME/.agents/skills/project-memory/` is the current Codex user-scope location. Codex also discovers repository-scoped skills under `.agents/skills/` from the working directory up to the repository root.

Claude Code user scope:

```bash
mkdir -p "$HOME/.claude/skills"
cp -R skills/project-memory "$HOME/.claude/skills/"
```

For a Claude Code project-scoped installation, copy the folder to `.claude/skills/project-memory/` in that project. Review any existing installation before copying an update so local customizations are not overwritten.

There are no background or automatic updates. Pull or download a release, review its changes, and update the plugin or standalone copy deliberately.

## Usage

Ask for the outcome in ordinary language. Codex can also invoke the skill as `$project-memory`; invocation syntax in Claude Code depends on whether it was installed as a plugin or standalone skill.

Initialize a new or loosely organized project:

```text
Use Project Memory to initialize durable project context here. Inspect the repository first, preserve existing documentation, and ask only the material decisions that belong to me.
```

Audit an existing project before migration:

```text
Use Project Memory to audit this project's current documentation without writing. Map canonical documents, conflicts, stale claims, missing entry rules, and the smallest safe migration.
```

Apply an approved migration:

```text
Use Project Memory to apply the approved migration in place. Preserve established paths and content, add only missing structure, and report every changed file.
```

Capture reusable experience:

```text
沉淀一下
```

This starts a review. It does not grant blanket approval: each proposed experience can be confirmed, edited, or skipped.

## Governed evolution

Project Memory does not wake itself on a timer. A periodic review happens only when the skill is invoked and a user requests a review or an agreed review trigger is due.

For a new or migrated long-lived project, it asks once whether reviews should follow milestones, run monthly, remain manual, or stay off. No answer means `manual`. Proactive reviews occur only at a natural checkpoint, require enough meaningful evidence, and respect the configured cadence and cooldown.

Version 1 of this workflow can apply only a reversible trial to the current project's memory protocol. It cannot change the installed skill, another project, this GitHub repository, a marketplace, or a published release.

During an evolution review, the skill should:

1. Show concrete evidence of recurring friction or a missed case.
2. Separate current-project fixes from reusable-skill ideas, and mark the latter out of scope for this workflow.
3. Present options, a recommendation, compatibility impact, migration needs, and a verification plan.
4. Ask the user to confirm, edit, defer, or reject each material change.
5. Apply only the explicitly approved current-project trial and record its rollback path.
6. Validate the result, gather outcome evidence, and ask separately whether to adopt, adjust, stop, or roll back the trial.

Approval to discuss an improvement is not approval to edit, publish, push, release, or update installed copies. Cross-project review and upstream promotion are outside the V1 workflow; they require a separate maintainer task with separately approved inputs, minimization, and redaction.

Example:

```text
Review this project's Project Memory protocol for governed evolution. Present evidence and alternatives, and do not modify the project until I approve a bounded, reversible trial.
```

## Updating an existing project

Updating the installed plugin or skill does not automatically rewrite projects that used an older version. In each project, run a read-only audit first and then approve an in-place migration. Project Memory should preserve existing conventions such as `CONTEXT.md`, `STATE.md`, `docs/adr/`, or an existing experience library instead of creating competing copies.

Commit or back up the project before a broad migration so the documentation diff is easy to review.

## Development

Keep human-facing documentation at the repository root. Keep only files needed by the agent under `skills/project-memory/`.

Run the repository tests from the root:

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py'
```

When the project validator is present, run it against a fixture or project root:

```bash
python3 skills/project-memory/scripts/validate_project_memory.py /path/to/project
```

Build deterministic standalone, Codex plugin, and Claude Code plugin archives:

```bash
python3 scripts/build_release.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) before changing behavior or templates.

## License

[MIT](LICENSE)
