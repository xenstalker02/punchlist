# Punchlist

![Punchlist — named-defect design audit](assets/social-preview.png)

[![Validate](https://github.com/xenstalker02/punchlist/actions/workflows/validate.yml/badge.svg)](https://github.com/xenstalker02/punchlist/actions/workflows/validate.yml)

**A set of instructions an AI coding agent loads before it inspects a build: 50 named interface defects, and one question asked of each. Is this one present here, and where.**

The agent does the walking. The list decides what counts as a defect and what evidence it has to produce, and it refuses to report anything it cannot point at.

That constraint is the whole design. Ask an AI to "review this screen" and you get a plausible essay nobody can act on or dispute. Ask it which of 50 named defects are present, with the location and the proof for each and the rest left out entirely, and it has to commit to something checkable.

The name comes from construction, where a building does not hand over until the punch list is cleared. An inspector walks the site and writes down every defect with a location and a required fix. Not "the lobby feels unfinished," but *outlet plate missing, east wall, second floor*.

> **Status: pre-release.** The taxonomy, the review pipeline, and the evaluation are all still moving. Don't build anything on the schemas yet.

## What the taxonomy covers

Fifty defects in three categories, each filed under one of fifteen single-word standards it violates.

| Category | Count | Standards |
|---|---|---|
| **Interface** | 20 | Coherent · Legible · Discoverable · Operable · Candid |
| **Content** | 16 | Plainspoken · Accurate · Constructive · Navigable · Considerate |
| **Behavior** | 14 | Truthful · Lossless · Reachable · Convergent · Reversible |

Three of them, to show what a file looks like rather than just the filing system. `swallowed-rule`: a style declaration that was authored but never reached computed style. `recall-tax`: structure the system computed and then made the user remember. `elided-series`: a chart rendering fewer categories than its data contains, with no way for the reader to tell.

Every definition is written as a presence test beginning *"Present when…"*, answerable yes or no against a real product. If an auditor can't answer yes or no, the definition is what's broken. All 50 entries carry at least one public-standard reference and a documented real instance; that is the bar for an entry shipping at all.

## Running it

A "skill" here is a folder an AI coding agent reads before it starts a task: one markdown file of instructions plus the taxonomy as JSON data. Install it with the `skills` CLI:

```
npx skills add xenstalker02/punchlist
```

Or clone it directly for Claude Code:

```
git clone https://github.com/xenstalker02/punchlist.git ~/.claude/skills/punchlist
```

Then ask it to audit a screen, a flow, or a build. Three things make the result better:

1. **Give it the running app if you can.** A live browser pass sees computed styles, focus, and cascade losses; source alone cannot. Both examples in the next section are invisible in source, which reads as correct in each case.
2. **Declare the severity basis before the sweep**, whether that's absolute usability, demo readiness, or something else. One run that did not state the lens first ranked keyboard-unreachable navigation below two cosmetic issues. That ranking made sense for screen-recording readiness and would have been misleading as a general usability judgment.
3. **Write a `conventions.md`.** Copy `conventions.example.md` into your project and record the decisions that are deliberate, each with an owner and a reason. Those stop being re-flagged on every run. An entry with no stated reason is how an accident hides as a convention.

Screenshots work too, and Figma works where the API exposes structure. Both see less, and both say so.

To validate the repository itself, run:

```
python scripts/validate.py
```

The validator enforces the schema and evidence requirements, including category counts of 20 interface, 16 content, and 14 behavior defects. It also validates the JSON examples and internal file references in this README and `SKILL.md`, and exits non-zero on failure. CI runs regression tests against deliberately broken copies of the taxonomy.

## The defects that survive longest are the ones that produce no error

Two real examples, from one production React app, both shipped past a build that passed.

**A callout with no background.** The element was styled `bg-[color-mix(in srgb, var(--sev-opportunity) 10%, transparent)]`. Tailwind doesn't emit a class for an arbitrary value containing spaces, so that rule was never generated at all. Nothing threw. The source still read as correct, and the callout looked like an ordinary paragraph of text, which is exactly what a designer reviewing a screenshot would take it for.

**A color that lost an argument with itself.** Three components each had two `labelStyle` attributes on one element. JSX keeps the last one, so the design token was silently discarded in favor of a hardcoded `rgba`. `vite build` reports this as a warning and exits 0, which means it scrolls past in a green build. Fixing the first instance is what surfaced the other two.

Neither produced an error, a failed test, or a red build. That is the class Punchlist exists for. A button that looks fine and does nothing can outlive a bug that crashes, because a crash recruits the whole team and a quiet wrong color recruits nobody. Both are named in the taxonomy as `swallowed-rule`, an entry that exists *because* of them.

## Why a named defect beats a review

It's falsifiable. "Poor information hierarchy" is an opinion. `long-distance-label`, defined as a label separated from its value by more empty distance than separates either from unrelated content, is a claim you can disprove by measuring.

It's also countable, so two audits of the same screen a month apart can be diffed. Prose can't. And it arrives with a location and a remedy, both of which the schema makes mandatory. A finding without a location is a vibe, and a finding without a fix is a complaint.

## Where the method comes from

Punchlist is grounded in inspection methodology that predates the current wave of AI design tools by about thirty years. It is not a ruleset produced by asking a model what makes a good interface.

Two traditions do the work. The first is **heuristic evaluation**, the inspection protocol behind the Nielsen Norman [ten usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/), in practice since the early 1990s. Two of its rules carry most of the weight: evaluators inspect independently and never see each other's findings, and severity gets rated *after* findings are merged, by all of them, rather than by whoever found the problem and is now attached to it. Punchlist's pipeline is that protocol with AI agents in the evaluator seats.

One caveat belongs right here, because it is the first thing an informed reader will raise. Heuristic evaluation gets its power from evaluators who are independent in a strong sense: different training, different blind spots, uncorrelated errors. Several agents run from one model are not independent in that sense, and giving each a distinct lens is a partial substitute rather than an equivalent. The rendered-pass failure below is what that looks like when it bites, and it is one more reason the detection eval matters more than the taxonomy does.

The second is the **tenets-and-traps tradition**, the practice of giving interface defects proper names instead of describing them in adjectives. It runs from software defect classification, through UI Tenets & Traps (Medlock and Herbst), to the deceptive-pattern catalogs (Brignull, and the FTC's 2022 staff report). A name makes the disagreement specific. What's left is whether it's present here.

**The taxonomy in this repo is an original derivation and reproduces no prior deck.** Its names, definitions, groupings, and the selection of what counts as a defect at all were written from a documented record of production defects and from public standards: WCAG 2.2, the GOV.UK Design System and style guide, Apple's Human Interface Guidelines, Material, and the Nielsen and Shneiderman heuristics.

## What a finding looks like

Here is one as a critic writes it, before severity is assigned: the callout from the section above.

| Field | Value |
|---|---|
| **defect** | `swallowed-rule` |
| **standard** | Coherent |
| **surface** | Collections, severity callout |
| **symptom** | The callout paints no background and reads as ordinary body text, so the severity distinction the design encodes is invisible. |
| **evidence** | CSSOM: 0 rules matched the authored class. Control siblings on the same page matched 6 and 10, so the query works. Tailwind emits nothing for an arbitrary value containing spaces. |
| **verified_how** | `rendered` |
| **fix** | Re-author without whitespace inside the bracket; composite over a real surface color rather than `transparent`. |
| **fixed_how** | `mechanical`, applied and then re-verified by re-sweeping the whole surface, not just the one defect. |

Symptom and evidence are separate fields, because a symptom is what a person experiences and evidence is proof. Keeping them apart is what stops the evidence field quietly filling up with opinion. `verified_how` records what kind of claim is being made, since measured in a live browser, read in source, and seen in an image are three different things, and collapsing them is how an audit gets trusted for the wrong reasons.

**The evidence names a control.** Zero matches and a broken query look identical, so a zero-match finding has to prove the query could have matched something. This rule is here because a run once reported a real defect class across an entire app when the browser surface simply wasn't compositing.

**Severity is absent when the finding is written.** It gets assigned afterwards by every critic on the merged list, 0 to 4, where a 0 is a veto meaning "this is not a defect." Findings averaging under 1 with any 0 vote are dropped and logged. Delaying the rating keeps the discoverer's first judgment from becoming the only one.

[`examples/compass-collections.json`](examples/compass-collections.json) is the machine-readable final state of a finding from the Compass Collections audit after severity assignment and repair.

## What it can see, and what it says instead of guessing

Every defect declares `detectable_from`, so a run knows which checks its input can support. A screenshot run executes a subset and lists the rest under **Not assessed** rather than guessing. Where one finding blocks the verification of another, the blocked one is reported as unverifiable, never as absent.

Where a cheap deterministic check exists, Punchlist runs the check instead of judging by eye. Each of these is in the repo because eyeballing got it wrong first:

| The question | The check |
|---|---|
| Is this text truncated, or did the screenshot's edge cut it? | `scrollHeight > clientHeight`, or a live `-webkit-line-clamp` |
| Is the chart showing all its data, or did the library drop labels that didn't fit? | rendered tick count vs series length |
| Is this contrast actually passing? | compute against the composited background, not the flat token |
| Did focus really move? | read `document.activeElement` after the transition, never the handler |
| Is this type handled? | check the consumer function, never `grep` the file |

A file-level grep can wrongly score a real defect as already fixed because the matches may be the instances somebody already corrected. `eval/baseline.md` has the worked case: six matches in the file, none in the function that renders.

## Where the instrument has been wrong

Two failure records ship with this repo, because a tool that documents only its successes is asking to be taken on faith.

**`eval/screenshot-false-positives.md`** covers an audit from six screenshots that reported two defects which did not exist. It read "summaries truncate mid-sentence" off text the photograph's edge had cut, and "the summary cites an account missing from its own chart" off a chart whose library had dropped the labels that didn't fit. Both wrong readings were pixel-identical to the true one, and both were the more alarming reading. In this audit, both errors skewed toward false alarms. That is the expensive direction: it spends the user's trust and sends someone to fix working code.

**`eval/rendered-pass-false-positives.md`** is the same shape, in the path meant to fix the first one. A live-browser run reported a hover-reveal mechanism broken across an entire app. The browser surface wasn't compositing, so CSS transitions never advanced and `getComputedStyle` returned every transitioned property's start value, permanently. There's no error and no null for that condition. A frozen page and a live page return the same kind of number.

Both produced permanent rules. A screenshot's absence is never evidence; evidence within ~24px of the frame edge gets downgraded; liveness is asserted before any rendered measurement; and a finding that a mechanism is broken *everywhere* is treated as evidence against itself, since a broken harness is likelier than a product that shipped with the mechanism universally dead.

One of those wrong findings also earned an entry. The claim "this chart is missing data" was false, but the condition it was reaching for was real and had no name: a chart can legitimately render fewer categories than its data contains, and the reader has no way to tell. That is `elided-series` now. Rejected findings get logged with a note on whether they imply a missing defect, and that log is the taxonomy's backlog.

## What is not claimed

No precision or recall figure appears anywhere in this repo. A detection eval against a pinned commit is designed (`eval/baseline.md`) and has not been run. When there's a number it will be per-defect and per-input-mode, with the misses published alongside it.

The evidence so far comes from one corpus. `eval/compass-coverage.md` shows the taxonomy could name 15 of 15 findings from a real audit, and that two of those entries didn't exist until that test demanded them. Coverage is a property of a vocabulary. It says nothing about how reliably a model detects, and nothing at all about a second codebase with a different stack.

The behavior category is the thinnest of the three. Most of its entries need interaction to observe, and the audit that grounded them was largely static, so their evidence is a documented defect record rather than a detection run.

And there is no score. Counts describe a sweep, they don't rank screens, and a surface with four findings isn't worse than one with two.

## What's in the repo

```
SKILL.md                  the instructions an agent reads: inputs, evaluator pipeline, fix tiers
scripts/validate.py        dependency-free validation for taxonomy, examples, counts, and references
tests/test_validate.py     pass and deliberate-failure fixtures for the validator
taxonomy/                 50 named defects, 3 categories, 15 standards
  interface.json  (20)
  content.json    (16)
  behavior.json   (14)
schema/
  defect.schema.json      what a taxonomy entry must contain
  finding.schema.json     what one audited instance must contain
conventions.example.md    copy into your project; records the decisions that are deliberate
examples/                  schema-valid output from a real audit
assets/social-preview.*    editable source and exported GitHub preview
eval/                     the coverage test, the pinned detection baseline, both failure records
.github/                   continuous validation and contribution templates
```

## License

MIT. See [`LICENSE`](LICENSE).
