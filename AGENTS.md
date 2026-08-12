# Repository contract

Punchlist is a named-defect taxonomy and an evaluator protocol. Keep changes narrow, checkable, and grounded in evidence.

## Taxonomy entries

- Write every definition as a presence test beginning `Present when`.
- Add a public-standard reference and a documented real instance to every entry.
- Keep defect ids unique, lowercase, and hyphen-separated.
- Put each defect in the category and standard that own it. Do not duplicate an entry to increase coverage.
- Do not add accuracy, prevalence, time-saved, or other numerical claims without a reproducible measurement committed alongside the claim.
- Preserve provenance. Borrow structure from other repositories when useful; do not copy their prose or taxonomy wording.

## Findings and examples

- Separate the user-visible symptom from the evidence that proves it.
- Record how the claim was verified. A screenshot, source read, rendered measurement, and interaction are different evidence.
- Declare the severity basis before assigning severity.
- Do not turn a rejected or unverified observation into a finding.

## Before committing

Run:

```sh
python scripts/validate.py
python -m unittest discover -s tests -v
```

Both commands must pass. If the validator changes, first add or update a test that fails for the behavior being added.
