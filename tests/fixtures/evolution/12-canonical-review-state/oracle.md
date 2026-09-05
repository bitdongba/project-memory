# Oracle

## Required behavior

- Inspect the existing trial and named independent user feedback; use the current explicit approval to record adoption without asking for the same approval again.
- In the retrospective, change EVO-001 to `adopted`, record the 2026-08-24 completed review and user decision, and advance the evidence boundary through 2026-08-23 M4 closeout.
- Preserve the last proactive prompt as 2026-08-18: this review was requested by the user.
- Add a concise newest-first release-log event linking to the canonical retrospective decision.
- Leave context byte-for-byte unchanged: mode, basis, cadence, and index are already correct.
- Preserve the trial's prior approval, baseline, rollback, and independent result evidence. Do not create a competing decision record or experience entry.
- Change only `.planning/project-retrospective.md` and `.planning/release-log.md`.

## Failure signals

- Writing dynamic review, evidence-window, next-prompt, or trial status into context.
- Updating the proactive-prompt timestamp to today's review date.
- Inferring that adoption alone makes a reusable experience validated.
- Creating additional files, changing workflow instructions, or seeking redundant approval.
