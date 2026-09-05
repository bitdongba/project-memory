# Collaborative evolution behavior fixtures

These fixtures test observable behavior, not implementation wording. Run each case in an isolated copy and give the test agent only:

1. the `project/` directory;
2. the case's `prompt.md` content;
3. the `project-memory` Skill under test.

Do not give `oracle.md` to the test agent. Use it only after the run to evaluate the response and file diff. This separation prevents the expected behavior from leaking into the forward test.

All cases use the fixed evaluation date `2026-08-24` so cadence and cooldown results remain deterministic. A runner may substitute another date only if it shifts every fixture date consistently.

Read-only cases should produce no project diff. Write cases permit only the
project-local files listed in the manifest and the changes described by the
oracle. Compare the entire before/after project tree, including stable context
and proactive-prompt dates. Never run these fixtures against a real project,
installed Skill directory, or GitHub checkout containing unpublished user work.

The unit tests validate fixture structure and read-only validator behavior;
they do not simulate or establish agent compliance. Run fresh-agent cases to
evaluate actual review decisions and emitted file diffs.

The cases cover:

- first-use mode selection and the manual fallback;
- the three-meaningful-task gate;
- a due review with no evidence-backed candidate;
- the three-candidate batch limit and required decision fields;
- the 14-day cooldown;
- rejected-candidate suppression;
- a high-impact event that may bypass cooldown;
- the current-project-only V1 boundary;
- applying an explicitly approved trial without self-modifying the Skill.
- requested reviews during cooldown, including legacy duplicate review dates;
- requested reviews in off mode with fewer than three tasks, without changing the preference;
- authorized completed-review and adoption records kept in the retrospective while stable context and the proactive-prompt timestamp remain unchanged.
