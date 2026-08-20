# Contributing to Punchlist

Punchlist accepts corrections, missing defects, and changes to the evaluator protocol. A change earns review by showing the evidence that supports it.

## Set up the development checks

Use Python 3.11. Local verification ran on Node 24.14.0. CI uses its runner-provided Node version, and no broader Node range is qualified yet. The only pinned JavaScript development dependency is `@playwright/test@1.62.1`; visual report checks use Playwright's Chromium browser.

```sh
python -m pip install -r requirements-dev.txt
npm install
npx playwright install chromium
python scripts/validate.py
python -m unittest discover -s tests -v
npm run test:report
```

The renderer runtime uses the Python standard library. Repository validation also inspects committed public PDFs with the dev-only PyMuPDF dependency from `requirements-dev.txt`. `npm run test:report` opens the synthetic report in Chromium and checks the print export.

For a local report, generate HTML directly from the canonical data and use the PDF command's data mode so it independently validates and renders the same inputs before printing:

```sh
python scripts/render_report.py --audit path/to/audit.json --report path/to/report.json --output output/report.html
npm run report:pdf -- --audit path/to/audit.json --report path/to/report.json --output output/report.pdf
```

Add `--theme` with the [bounded accent adapter](themes/platform-accent.example.json) to both commands when testing platform accents. The `--input` mode is only for verifying the [committed synthetic fixture](examples/synthetic/report.html); arbitrary HTML is intentionally rejected.

## Before opening a change

For a taxonomy entry, include:

- a unique, concrete defect name;
- a `Present when` definition that can be answered yes or no against a product;
- at least one public-standard reference;
- a generic, explicitly non-evidentiary illustration;
- honest `detectable_from` values; and
- a fix pattern that changes the condition named in the definition.

Use the missing-defect issue template if the category or wording still needs discussion. Use an RFC for changes to schemas, scoring, evaluator order, or fix tiers.

## Validate locally

CI runs on Python 3.11. Run the same checks before opening a pull request:

```sh
python -m pip install -r requirements-dev.txt
python scripts/validate.py
python -m unittest discover -s tests -v
npm run test:report
```

The validator checks taxonomy schemas, required evidence fields, synthetic report traceability, public-safety rules, and documentation links. Keep generated examples synthetic. Do not include a real organization’s audit, private evidence, local paths, credentials, or customer identifiers.

## Pull requests

Keep one argument per pull request. State what changed, name the evidence, and say what you deliberately left alone. For report work, identify the canonical audit and projection inputs, confirm that a recipient can trace displayed claims to stable IDs, and attach public synthetic evidence for visual changes. Do not include a benchmark result unless another person can reproduce it from material in the repository.

By contributing, you agree that your work is licensed under the repository's MIT License.
