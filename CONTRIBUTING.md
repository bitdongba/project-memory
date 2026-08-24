# Contributing

Thank you for improving Project Memory. Contributions should preserve user control, project portability, and the distinction between human intent and current operational evidence.

## Before opening a change

- Search existing issues and pull requests for the same behavior.
- Describe a concrete failure mode or repeated source of friction.
- Remove secrets, personal data, private repository names, and identifying local paths from examples.
- For a material behavior change, explain alternatives, compatibility impact, migration needs, and how the change will be verified.
- Use an issue or proposal first when the change alters authority boundaries, default files, approval behavior, compatibility, or release policy.

## Repository boundaries

- `skills/project-memory/` is the standalone skill and the canonical skill source.
- `.codex-plugin/plugin.json` and `.claude-plugin/plugin.json` package that same source for their respective hosts.
- README files, changelog, contribution guidance, and release engineering stay at the repository root; do not copy them into the skill folder.
- Generated ZIP files and checksums are release artifacts. Do not edit or commit them as source.
- Keep Codex and Claude Code behavior aligned unless a difference is genuinely host-specific and documented.

## Design rules

Changes must continue to enforce these rules:

1. Preserve existing project documentation and established canonical paths.
2. Do not turn an inference into a fact or user decision.
3. Verify changeable operational claims against primary evidence.
4. Ask the user only for decisions they own and only when the choice materially affects the outcome.
5. Require individual review before promoting reusable experience.
6. Never silently scan unrelated projects, mutate the reusable skill, publish, push, release, or update installed copies.
7. Keep secrets and unnecessary personal information out of project memory and test fixtures.
8. Preserve exact negative requirements, ordering guarantees, numerical defaults, and acceptance criteria.

## Making a change

1. Edit the canonical source rather than a generated artifact.
2. Keep `SKILL.md` concise and move detailed scaffolds into a directly linked reference when needed.
3. Update both plugin manifests when release metadata or packaged capabilities change.
4. Update both READMEs when installation, safety, or user-facing behavior changes.
5. Add or revise a fixture for behavior changes.
6. Add an `Unreleased` changelog entry.

Do not add a version field to skill frontmatter. Versions belong in Git tags, plugin manifests, release notes, and artifact names.

## Validation

Run the unit tests from the repository root:

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py'
```

When the project validator is present, exercise it against a fixture or a redacted local project:

```bash
python3 skills/project-memory/scripts/validate_project_memory.py /path/to/project
```

Build release archives into the ignored `dist/` directory and inspect their contents:

```bash
python3 scripts/build_release.py
```

Before submitting a pull request, also confirm:

- both plugin manifests parse as JSON and use the same version;
- skill frontmatter and `agents/openai.yaml` parse correctly;
- all relative Markdown links resolve;
- the packaged skill contains only required agent-facing files;
- no `.DS_Store`, editor state, credentials, personal paths, or generated archives are included;
- direct, indirect, negative, and boundary prompts have been considered for behavior changes.

Forward tests are evaluations, not demonstrations. Give the evaluator the raw skill and realistic task without leaking the expected answer or prior diagnosis.

## Pull requests

Keep pull requests focused. Include:

- the observed problem and evidence;
- the chosen approach and rejected alternatives;
- affected hosts and compatibility impact;
- migration notes, if any;
- validation commands and results;
- confirmation that examples and fixtures are safe to publish.

By contributing, you agree that your contribution is licensed under the repository's [MIT License](LICENSE).
