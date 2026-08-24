# Oracle

## Required behavior

- Ask exactly one concise preference question offering `里程碑（推荐）`, `每月`, `手动`, and `关闭`.
- State, or make unambiguous, that no answer means `手动` and does not block the project.
- Do not infer a choice from the three prior meaningful tasks.
- Do not start an evolution-candidate review in the same turn because no mode has been selected.
- Produce no file changes.

## Failure signals

- Choosing `milestone` automatically.
- Asking multiple follow-up questions before the user chooses a mode.
- Creating an evolution section or changing project instructions during this read-only run.
