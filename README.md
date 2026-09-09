![Punchlist cover with an orange background, the Punchlist wordmark, and three illustrated steps for an evidence-based UX review](assets/social-preview.png)

[![Validate](https://github.com/xenstalker02/punchlist/actions/workflows/validate.yml/badge.svg)](https://github.com/xenstalker02/punchlist/actions/workflows/validate.yml)

Punchlist helps designers use AI for a focused UX review. Give it one user task and an authorized URL, screenshot, Figma frame, or codebase. It returns named issues, the evidence behind them, what worked, and what it could not check in a readable HTML or PDF report.

The checks are loosely informed by Nielsen Norman Group's usability heuristics and other established UX practices. Each finding must point to something the reviewer inspected.

> **Status: v0.1, early release.** The review and report tools have automated checks, but Punchlist has only been tried on a couple of designs so far. Detection accuracy has not been measured. Treat findings as review input and check them before acting. See [Known limits](#known-limits).

## Start here

- **Preview the result:** open the [synthetic PDF report](examples/synthetic/report.pdf). Developers can also inspect the [HTML source](examples/synthetic/report.html).
- **Run an audit:** install Punchlist with `npx skills add xenstalker02/punchlist`.
- **Render reports locally:** clone the repository and follow [Render HTML and PDF](#render-html-and-pdf).

The examples use an invented product and invented evidence. They show the recipient-facing output without exposing an audit of a real organization.

## What you get

- A review organized around one real task, not a loose screen critique.
- Named defects with stable IDs, evidence, severity reasoning, and next steps.
- What supported the task, plus a visible **Not assessed** section so silence is not mistaken for approval.
- A self-contained HTML report and an optional PDF rendered and visually checked in Chromium.
- Claims limited to what the supplied URL, screenshot, Figma frame, or code can demonstrate.

Punchlist does not turn defect counts into a score or a verdict on the whole product.

## Try your first audit

Install the skill with an AI tool that supports Agent Skills:

A skill is a set of instructions and tools you add to an AI assistant. Punchlist needs an assistant that can read files and run local commands; it is not a standalone website. If you only want to see what it produces, start with the [sample PDF](examples/synthetic/report.pdf).

```sh
npx skills add xenstalker02/punchlist
```

Or clone the repository into a local Claude Code skill directory:

```sh
git clone https://github.com/xenstalker02/punchlist.git ~/.claude/skills/punchlist
```

After installing, give your AI tool a prompt like this:

```text
Use Punchlist to review [URL or attached screenshot]. A new visitor, signed out on mobile, starts at a product page and tries to compare two options. Use the experience profile. Rate severity by impact on completing the comparison.
```

Punchlist produces a structured review record and a readable report when the AI tool has the required local tools. File rendering depends on that tool's available Python, Node.js, Playwright, and browser access.

Use this neutral template for your own review:

```text
A `[user]`, in `[state]` on `[device]`, starts at `[entry point]` and tries to `[complete task]`; `[profile]` profile. Severity basis: `[basis]`.
```

Choose `experience` for a product, screen, or flow. Choose `implementation` for accessibility, semantics, code, conformance, or design-system QA. Declare the severity basis before inspection so every critic rates the same kind of task impact.

## How Punchlist works

```text
task brief + authorized input -> evidence-based review -> HTML/PDF report
```

1. **Describe the task.** Say who is using the product, what state they are in, what device they are on, where they start, and what they are trying to do.
2. **Inspect the allowed material.** Review only the live product, screenshots, Figma work, or code included in the brief.
3. **Name the issues.** Match observations to Punchlist's 50 named checks, combine duplicates, and put anything the evidence cannot answer under **Not assessed**.
4. **Keep the evidence attached.** The review record stores the scope, source, screenshots or code references, decisions, gaps, and limits behind each finding.
5. **Hand off a readable report.** Punchlist turns that record into a self-contained HTML report and, when requested, a PDF.

The report is deliberately cautious: it counts only supported findings and rejects unresolved IDs, unsafe values, unapproved evidence, or failed redaction checks.

## Capability matrix

| Mode | What it needs | What it can establish |
| --- | --- | --- |
| Single-agent minimum | One agent and an authorized URL, screenshot, or Figma input | A bounded audit bundle. Checks without supporting evidence stay under **Not assessed**. |
| Multi-critic review | Three to five separate critic passes, plus browser or Playwright access for live behavior | Separately produced observations, a recorded outcome for every applicable taxonomy check, merged severity decisions, and an evidence-led report. |
| Screenshot or Figma | A supplied frame or available structural read | Pixel and exposed structural checks. It cannot prove omission, reachability, or behavior outside the captured state. |
| Render and PDF | Python for HTML; Node, Playwright, and Chromium for PDF and visual tests | Self-contained HTML, plus a browser-verified PDF of the same report. |

Multi-critic review is the protocol's intended evaluation method. A single agent can still assemble a useful, limited report when it keeps the limits of its evidence visible.

## Privacy and authorization

Preflight defaults to **public and logged-out** surfaces. Authenticated, private, customer, employer, or NDA-bound material needs explicit scope and an `authorized-restricted` classification before inspection. Restricted evidence and output remain restricted unless publication receives separate approval.

Before sharing material with critics, record the authorized surfaces, permitted recipients, whether external or model subagents may receive evidence, allowed evidence types, and retention requirements. Redact local paths, credentials, private URLs, personal emails, customer identifiers, and unapproved screenshots. `.gitignore` keeps generated files out of a normal commit; it does not protect confidential data.

Private review records can be validated before sharing approval. Creating a report for a recipient is a separate step and requires approval for that recipient and the included evidence. A private record passing validation does not grant permission to render or share it.

## Render HTML and PDF

HTML generation uses Python 3.11 and the standard library. The PDF workflow additionally uses Node.js 24.14, npm 11.9, the locked JavaScript dependencies, and Playwright Chromium.

From a cloned repository, prepare the PDF runtime once:

```sh
npm ci
npx playwright install chromium
```

Create the ignored `output/` directory, then run the committed synthetic example as a smoke test:

```sh
python scripts/render_report.py --audit examples/synthetic/audit.json --report examples/synthetic/report.json --output output/report.html
npm run report:pdf -- --audit examples/synthetic/audit.json --report examples/synthetic/report.json --output output/report.pdf
```

Replace the two example JSON paths with your own validated audit and report data when you are ready to render a real review.

The PDF command validates and renders the data again into a unique ignored temporary file, prints only that self-contained result, and removes it. It never accepts an arbitrary HTML file. HTML input mode is reserved for verifying the committed synthetic fixture:

```sh
npm run report:pdf -- --input examples/synthetic/report.html --output output/synthetic-report.pdf
```

### Optional platform accent

Pass the same adapter to both data commands:

```sh
python scripts/render_report.py --audit path/to/audit.json --report path/to/report.json --theme themes/platform-accent.example.json --output output/report.html
npm run report:pdf -- --audit path/to/audit.json --report path/to/report.json --theme themes/platform-accent.example.json --output output/report.pdf
```

In v0.1, a platform accent may change the platform name, primary accent, supporting tone, evidence treatment, and visible source reference. It cannot change the default typography, grid, spacing, report anatomy, project attribution, evidence hierarchy, severity language, or accessibility requirements.

## Report appearance

The default `punchlist-default` theme uses an editorial hierarchy, evidence frames, square geometry, restrained deep-sapphire emphasis, and accessible public font fallbacks. Generated reports do not render platform logos in v0.1; an approved public logo is a separately directed Figma or social-cover capability.

Every report uses the project attribution `Punchlist · Independent experience review`. The default report contains no personal byline or portfolio link.

## Validation

The renderer runtime uses the Python standard library. Full repository validation also inspects committed public PDFs with the dev-only PyMuPDF dependency from `requirements-dev.txt`; browser checks need the development dependencies and Chromium described in [CONTRIBUTING.md](CONTRIBUTING.md).

```sh
python -m pip install -r requirements-dev.txt
python scripts/validate.py
python -m unittest discover -s tests -v
npm run test:report
```

These checks cover the taxonomy, schemas, synthetic bundle, public-safety rules, documentation links, internal references, and the report's browser and print output.

## Known limits

- Several agents using the same model do not have the independence of evaluators with different training and experience.
- Input constrains the claim: a screenshot cannot prove that a control is unreachable or that content is absent beyond its frame.
- Browser verification depends on a locally installed Chromium browser; HTML generation still works without it.
- The repository makes no precision, recall, coverage, or time-saved claim. A report is evidence for one declared task, not a quality certification.

## Contributing and support

Read [CONTRIBUTING.md](CONTRIBUTING.md) for local setup and evidence expectations, [SUPPORT.md](SUPPORT.md) for compatibility and issue help, [SECURITY.md](SECURITY.md) for vulnerability reporting, and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for participation standards. Maintainers use [RELEASING.md](RELEASING.md) for every authorized release.

## License

MIT. See [LICENSE](LICENSE).
