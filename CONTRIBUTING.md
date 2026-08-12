# Contributing to Punchlist

Punchlist accepts corrections, missing defects, and changes to the evaluator protocol. The useful contribution is the evidence, not the volume of the diff.

## Before opening a change

For a taxonomy entry, include:

- a unique, concrete defect name;
- a `Present when` definition that can be answered yes or no against a product;
- at least one public-standard reference;
- a documented real instance;
- honest `detectable_from` values; and
- a fix pattern that changes the condition named in the definition.

Use the missing-defect issue template if the category or wording still needs discussion. Use an RFC for changes to schemas, scoring, evaluator order, or fix tiers.

## Validate locally

CI runs on Python 3.11, and the validator has no third-party runtime dependencies.

```sh
python scripts/validate.py
python -m unittest discover -s tests -v
```

The validator checks the taxonomy schemas, fixed category counts, required evidence fields, example findings, and internal references in `README.md` and `SKILL.md`.

## Pull requests

Keep one argument per pull request. State what changed, name the evidence, and say what you deliberately left alone. Do not include a benchmark result unless another person can reproduce it from material in the repository.

By contributing, you agree that your work is licensed under the repository's MIT License.
