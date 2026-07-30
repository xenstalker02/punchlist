# Punchlist

**A named-defect design audit for AI agents.** In construction, a building doesn't hand over until the punch list — the inspection's enumerated list of defects, each with a location and a required fix — is cleared. Punchlist is that instrument for product UI.

> Status: pre-release. The taxonomy, review pipeline, and evaluation numbers are under active construction. Do not depend on the schema yet.

## Why named defects

Ask an AI to "review this UI" and you get a plausible essay. Ask it *which of these named defects are present — cite the location, cite the evidence, omit the rest* and it has to commit. Enumerability is the anti-slop mechanism:

- A named defect is **falsifiable** — a finding you can dispute with evidence, not an opinion.
- Named defects are **countable and diffable** — two audits of the same screen can be compared.
- Every finding carries a **location and a remedy** — a finding without a location is a vibe.

The defect class this tool exists for: **everything rendered fine, nothing errored, no test failed — and the product is still broken.** A save toast over state that was never persisted. A count pill disagreeing with its own list. A feature whose only entry point never renders on first load. These are the defects that live longest, because nothing names them.

## What it does

1. **Audit** — runs the taxonomy against your input (screenshot, live app via rendered inspection, or Figma) using an evaluator pipeline modeled on the heuristic-evaluation method: multiple independent critics, merged findings, severity rated post-merge by all critics with a built-in false-positive veto.
2. **Report** — findings as data, never a grade: `{defect, surface, symptom, evidence, severity, fix}` plus an explicit *could-not-verify* section for what the input cannot support.
3. **Fix, tiered by falsifiability** — mechanical fixes applied and re-verified by a full re-sweep of the touched surface; structural fixes proposed as diffs; judgment calls reported and routed into your project's declared conventions. Fixes apply to code; Figma and screenshot inputs get findings and proposals.

## One line beats an opinion

Most design-review output is argument. Where a deterministic check exists, Punchlist runs it instead — and these are not hypothetical, each one is here because eyeballing got it wrong first:

| The question | The check |
|---|---|
| Is this text really truncated, or did the screenshot's edge cut it? | `scrollHeight > clientHeight`, or a live `-webkit-line-clamp` |
| Is the chart showing all its data, or did the library drop labels that didn't fit? | rendered tick count vs series length |
| Is this contrast actually passing? | compute against the composited background, not the flat token |
| Did focus really move? | read `document.activeElement` after the transition, never the handler |
| Is this type handled? | check the **consumer function**, never `grep` the file |

Each of those replaced a confident wrong answer. The first two caught a reviewer reporting two defects that did not exist; the last one is how a real defect gets scored "already fixed", because the mentions that satisfy a file grep are usually the halves somebody already corrected.

## Honesty mechanisms

- Each defect declares `detectable_from` — a screenshot run lists what it could not assess rather than guessing.
- Findings distinguish `verified_how`: measured-in-browser vs read-in-source are different claims.
- Your project declares its conventions once (`conventions.md`); deliberate choices stop being re-flagged.
- The finder is never the fixer; the fixer is never the verifier.

## Lineage

Punchlist's method descends from the heuristic-evaluation tradition — Jakob Nielsen's ten usability heuristics and evaluation protocol ([nngroup.com](https://www.nngroup.com/articles/ten-usability-heuristics/)) — and from the named-defect taxonomy lineage that runs from software defect classification through UI Tenets & Traps (Medlock & Herbst) to the deceptive-pattern catalogs (Brignull; FTC 2022). The taxonomy here is an original derivation from documented production defects and public standards (WCAG 2.2, GOV.UK, Apple HIG, Material); it reproduces no prior deck.

## License

MIT © Punchlist contributors
