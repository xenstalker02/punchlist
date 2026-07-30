# Failure case — two false positives from a screenshot audit

**Why this file exists:** the tool treats screenshot input as primary, because it is the path that works for a designer with no dev tooling. This is the documented case for why that path needs guardrails rather than trust. It is kept as a failure record, not a footnote — the detection rules in `SKILL.md` exist because of it.

## What was reported, and what was true

An audit run from six screenshots of a live product returned two defects on one screen. Both were wrong, and both were checked against the DOM afterwards.

**Claim 1 — "summaries truncate mid-sentence."** Evidence offered was two quoted fragments ending mid-clause: `"…with Ridgeline Cancer Institute at"` and `"…now representing 34% of"`. Reality: both summaries render complete, with terminal punctuation. A search for `-webkit-line-clamp` with `scrollHeight > clientHeight` returned **zero** elements — there is no clamp anywhere in the app. **The screenshot frame had cut the card off.**

**Claim 2 — "the summary cites an account that doesn't appear in its own chart."** The visible bars read three account names; the summary named a fourth. Reality: that account **is** in the chart — the top bar. The series has ten accounts, and the chart library elides axis labels that do not fit, so only three were painted. **The data was complete; the labels were not.**

## The class

**A screenshot cannot distinguish content the product truncated from content the frame cut, nor data the product omitted from labels the chart library elided.** The two readings are pixel-identical.

The dangerous property is the bias, not the error rate. In both cases the wrong reading was the **more alarming** one — a truncation bug and a data-integrity bug, rather than a photograph with edges. A screenshot-only auditor therefore fails toward **false alarms**, not toward silence, and false alarms are the expensive direction: they spend the user's trust on the first run, and they send someone to fix working code. Both false positives sat at the frame edge.

## What changed as a result

1. `verified_how` gained **`frame-limited`** — a finding whose only evidence is an image is a different epistemic object from one measured in the DOM. It is recorded as a question for a rendered pass, never as a defect.
2. The screenshot adapter **distrusts its own edges**: evidence within ~24px of the image boundary is excluded or downgraded.
3. `SKILL.md` states the rule directly — **when the input is a screenshot, absence is not evidence.** Missing labels, cut sentences, and absent controls are all things a frame can manufacture.
4. Deterministic checks replaced eyeballing where they exist: `scrollHeight > clientHeight` for clamped text, rendered tick count vs series length for charts.

## The real defect underneath

The investigation produced one genuine finding, which is the honest counterweight: **a chart can legitimately show fewer categories than its data contains, and the reader has no way to tell.** Ten accounts, three painted labels, no indication that seven were dropped. That is now `elided-series` — and note that it is a defect about the *chart's* honesty, not the data inconsistency originally claimed. The false positive and the true positive were adjacent, which is exactly why the check has to be mechanical.
