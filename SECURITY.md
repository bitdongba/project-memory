# Security Policy

Project Memory is an instruction-based plugin that reads and writes local project documentation through its host agent. Its security boundary is the host's sandbox, approval policy, and the directories the user places in scope.

## Supported versions

| Version | Security fixes |
|---|---|
| 0.1.x | Supported |
| Earlier prototypes | Not supported |

## Reporting a vulnerability

Use the repository's private security advisory feature when it is available. Do not put exploit details, secrets, private project content, or identifying paths in a public issue.

If private advisories are not available, open a minimal public issue asking the maintainers to establish a private reporting channel. Include no sensitive technical detail until a private channel is confirmed. No public security-response email is listed because the project has not verified one.

Useful reports include:

- a minimal redacted reproduction;
- affected Project Memory version and host;
- expected and actual authority or approval behavior;
- the files or data classes exposed to risk;
- whether the issue requires a malicious prompt, repository content, or package;
- suggested mitigation, if known.

## Security-relevant behavior

Please report behavior that could cause Project Memory to:

- persist a secret or unnecessary personal data;
- overwrite or delete existing project documentation without explicit authority;
- silently turn an assumption into a fact or user decision;
- scan projects outside the scope the user approved;
- expose absolute local paths or private project content in reusable examples;
- modify its own canonical source or an installed copy without explicit approval;
- publish, push, open a pull request, create a release, or fetch an update without explicit approval;
- bypass the host's sandbox or approval policy;
- package undeclared scripts, hooks, MCP servers, or external connections;
- allow a malicious project document to expand the task's authority.

Ordinary disagreements about writing style or document organization are not security issues unless they create one of the authority, integrity, privacy, or scope failures above.

## Data handling

Project Memory has no background service, telemetry, lifecycle hook, MCP server, or automatic updater. It does not require an account or send project memory to a service of its own. A bundled validator runs locally and only when explicitly invoked.

The host agent may still use tools or services available in the active session. Those tools retain their own permission, authentication, and data-handling rules.

Project memory may contain requirements, decisions, collaboration preferences, commands, and recovery references. Users should:

- never store credentials, tokens, private keys, or unredacted secret values;
- prefer repository-relative paths over home-directory paths;
- redact private names and data before contributing fixtures or issue reports;
- review `.planning/`, `AGENTS.md`, and `CLAUDE.md` before committing or publishing them;
- keep sensitive project memory out of public repositories;
- inspect release checksums and diffs before deliberate manual updates.

## Governed evolution boundary

An evolution review may inspect only sources inside the current audited project. In V1, approval may authorize one bounded, reversible current-project trial; it never authorizes editing the installed Skill, another project, this repository, a marketplace, or a release. Proposal review is not permission to publish, push, scan another project, or update an installed copy. Each expansion of scope or external action requires a separate workflow and explicit authority.

Cross-project evidence is outside the V1 evolution workflow. If a future, separately authorized maintainer task uses it, the evidence must be minimized and redacted. Raw private project content must not be copied into this public repository.
