# Punchlist

![Punchlist — task-led UX audit with named defects and evidence](assets/social-preview.png)

[![Validate](https://github.com/xenstalker02/punchlist/actions/workflows/validate.yml/badge.svg)](https://github.com/xenstalker02/punchlist/actions/workflows/validate.yml)

**Punchlist is a task-led UX audit for AI coding agents. It follows a real user journey, checks that journey against 50 named defects across interface, content, and behavior, and reports only the breakdowns it can prove.**

Use `experience` for a product, flow, or screen. Use `implementation` when the request is explicitly about accessibility, semantics, code, conformance, or a design system. Both return the same fields: defect, surface, symptom, evidence, severity, and fix.

The name comes from construction. An inspector does not write "the lobby feels unfinished." The punch list says *outlet plate missing, east wall, second floor*.

> **Status: pre-release.** The taxonomy, review pipeline, and evaluation are still moving. Do not build against the schemas yet.

## Install

```sh
npx skills add xenstalker02/punchlist
```

Or clone it directly for Claude Code:

```sh
git clone https://github.com/xenstalker02/punchlist.git ~/.claude/skills/punchlist
```

Then ask your agent to audit a URL, screenshot, or Figma file using the brief below. The full method requires an agent that can launch three to five independent subagents; live-app checks also require browser or Playwright access. Without those capabilities, interaction checks remain unassessed.

## Run an audit

Start with an evaluation brief:

```text
A first-time vinyl buyer, signed out on desktop, starts from a known album
and tries to choose one edition to buy; experience profile.
Severity basis: first-time purchase.
```

Punchlist needs a user, task, entry point, state or device, output profile, and severity basis. If the profile is omitted, it uses `experience`.

| Profile | Use it for | What leads the report |
|---|---|---|
| `experience` | Product, flow, screen, or unspecified UX audits | Task progress, mental models, decisions, feedback, trust, and recovery |
| `implementation` | Accessibility, semantics, code, conformance, or design-system QA | Operability, rendered measurements, and source-to-output failures |

A live app supports the fullest sweep. Screenshots run only checks their pixels can support; Figma adds structural evidence where its API exposes it. Anything the input cannot prove appears under **Not assessed**.

Three inputs improve the result:

1. The running product, when available.
2. A declared severity basis, written before inspection.
3. A project `conventions.md`, copied from [`conventions.example.md`](conventions.example.md), for intentional exceptions.

## How it works

1. **Orient.** Complete the task once without flagging defects. Record what already supports the task.
2. **Inspect.** Three to five critics work independently with distinct lenses and return only named, evidenced findings.
3. **Merge and rate.** Duplicate findings merge before every critic rates severity from 0–4. Severity is the mean; findings averaging below 1 with at least one 0 vote are logged and dropped.
4. **Report.** Canonical finding data stays machine-checkable. The optional human report uses [`templates/experience-review.md`](templates/experience-review.md) to lead with the task, user symptom, and smallest useful recommendation.

Counts describe the sweep. They are not a product score.

## Taxonomy

Fifty defects sit under fifteen standards:

| Category | Count | Standards |
|---|---:|---|
| **Interface** | 20 | Coherent · Legible · Discoverable · Operable · Candid |
| **Content** | 16 | Plainspoken · Accurate · Constructive · Navigable · Considerate |
| **Behavior** | 14 | Truthful · Lossless · Reachable · Convergent · Reversible |

Each definition begins with *"Present when…"* and must be answerable yes or no against a real product. Every shipped entry has a public-standard reference and a documented instance.

Three examples:

- `recall-tax` — the product makes someone remember information it already holds and could display.
- `swallowed-rule` — an authored style never reaches computed output.
- `elided-series` — a chart renders fewer categories than its data contains without making the omission visible.

Accepted findings follow [`schema/finding.schema.json`](schema/finding.schema.json): primary defect, surface, user-visible symptom, evidence, verification method, severity, and required fix. See [`examples/compass-collections.json`](examples/compass-collections.json) for a schema-valid result.

## Evidence boundaries

Punchlist records what it can verify and says what it could not assess. A screenshot cannot prove that content is absent, that a control is unreachable, or that a cropped sentence was truncated by the product. A live value is not trustworthy until the browser surface itself is shown to be working.

Cheap deterministic checks replace visual judgment when possible: rendered counts against source data, computed contrast against the composited background, `document.activeElement` after focus changes, and function-scoped source inspection instead of file-wide search.

The failure records are part of the instrument:

- [`eval/screenshot-false-positives.md`](eval/screenshot-false-positives.md)
- [`eval/rendered-pass-false-positives.md`](eval/rendered-pass-false-positives.md)
- [`eval/baseline.md`](eval/baseline.md)

## Method and limits

Punchlist combines Nielsen-style heuristic evaluation with the tenets-and-traps practice of naming recurring interface failures. The taxonomy is an original derivation grounded in production defects and public guidance from WCAG 2.2, GOV.UK, Apple, Material, Nielsen, and Shneiderman.

Its limits are explicit:

- Several agents from one model are not independent in the same way as evaluators with different training and blind spots.
- No precision or recall figure is claimed. The pinned detection evaluation is designed and has not been run.
- Current coverage evidence comes from one corpus; see [`eval/compass-coverage.md`](eval/compass-coverage.md).
- Behavior is the thinnest category because most entries require interaction to observe.

## Repository

```text
SKILL.md                    audit instructions and evaluator pipeline
taxonomy/                   50 named defects in three categories
schema/                     defect and finding contracts
templates/                  audience-facing experience report
examples/                   schema-valid audit output
eval/                       coverage, baseline, and failure records
scripts/validate.py         dependency-free repository validator
tests/test_validate.py      passing and deliberate-failure fixtures
assets/social-preview.*     editable source and GitHub preview
```

Validate the repository with:

```sh
python scripts/validate.py
python -m unittest discover -s tests -v
```

## License

MIT. See [`LICENSE`](LICENSE).
