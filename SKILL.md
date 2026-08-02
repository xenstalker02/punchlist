---
name: punchlist
description: Named-defect design audit. Use when asked to review, audit, or critique a UI, screen, flow, or product surface — or when asked "what's wrong with this design". Runs an enumerable defect taxonomy (Interface · Content · Behavior) through independent critics with post-merge severity rating, returns findings as data with locations and evidence, and applies mechanical fixes verified by re-sweep. Not for generating new designs.
---

# Punchlist — the named-defect design audit

You are running a punch-list inspection, not writing a review. The output is a list of **named defects, each with a location, evidence, and a required fix** — never prose impressions. If a defect from the taxonomy is not present, it does not appear. If the input cannot support a check, say so in *Not assessed* — never guess.

## Inputs, in order of preference

1. **Live rendered app** (browser/Playwright available) — full taxonomy. Source reading alone is FORBIDDEN for interface/behavior checks: dead CSS, cascade losses and unfired branches are invisible in source. Read computed styles and the live DOM. The rendered pass has its own failure mode, documented with the incident in `eval/rendered-pass-false-positives.md`: **a value is not evidence that the value was produced.** Assert the surface is compositing before measuring anything transitioned, and treat a mechanism that appears broken *everywhere* as evidence against the finding rather than for it.
2. **Screenshot(s)** — run only defects whose `detectable_from` includes `screenshot` or `content-text`. List every skipped defect under *Not assessed*. Obey the frame rules below; they are not optional.
3. **Figma** (MCP available) — as screenshots, plus structural reads where the API provides them.

### When the input is a screenshot, absence is not evidence

A frame can manufacture every one of these: a sentence that stops mid-word, a chart missing most of its categories, a control that isn't there, a list that appears to end. **An image cannot distinguish content the product truncated from content the frame cut, nor data the product omitted from labels the chart library elided.** Both readings look identical in pixels — and the wrong one is always the more alarming one, so a screenshot auditor is biased toward false alarms rather than toward silence. That is the expensive direction: it spends the user's trust on the first run.

Rules:

- **Distrust your own edges.** If the evidence for a finding sits within ~24px of the image boundary, do not report it as a defect. Either exclude it or record it with `verified_how: frame-limited`, phrased as a question for a rendered pass to answer.
- **Never infer omission from a screenshot.** Missing labels, absent controls, and short lists are `frame-limited` observations, never findings.
- **Escalate rather than guess.** A frame-limited observation that matters is a reason to request a rendered pass, not a reason to lower the evidence bar.

### Detection rules that beat eyeballing

Where a cheap deterministic check exists, run it instead of judging by eye:

| Question | Check |
|---|---|
| Is this text actually clamped? | `scrollHeight > clientHeight` on the element, or a live `-webkit-line-clamp`. No match means the sentence is complete and the *frame* cut it. |
| Does the chart show all its data? | Rendered tick/label count vs series length. Fewer ticks than data means `elided-series`, not missing data. |
| Is this row/list complete? | Rendered child count vs the source array length. |
| Is the contrast real? | Compute against the composited background, not the flat token. |
| Did focus actually move? | Read `document.activeElement` after the transition; never infer from the handler. |

## Before the sweep

1. Read the project's `conventions.md` if present. A finding that contradicts a declared convention is recorded under *Convention overrides*, not as a defect.
2. Declare the audit's **severity basis** (e.g. "absolute usability", "demo readiness") — before any finding exists. All severity ratings score against the declared bases only.
3. **Orientation pass**: walk the surface once to understand what it is for. No flagging during orientation.

## The sweep (evaluator pipeline)

Modeled on the heuristic-evaluation protocol (Nielsen): evaluators are independent, severity comes after merge.

1. **3–5 independent critics** (subagents), each briefed with: the taxonomy, the product/domain context, the conventions file, and a distinct lens (e.g. first-use walkthrough · state/persistence prober · content reader · keyboard-only operator). Critics never see each other's findings. Critics never saw the code they'd be grading being written (maker ≠ checker).
2. Each critic returns findings as the pre-merge subset of `schema/finding.schema.json`: primary `defect`, `surface`, `symptom`, `evidence`, `verified_how`. No severity yet, so this stage does not validate against that schema and is not meant to. Findings validate once step 4 has assigned severity.
3. **Merge**: deduplicate by defect + surface; genuine one-instance-two-defects cases use `also_matches`, one row.
4. **Severity questionnaire**: the merged list goes back to every critic; each rates every finding 0–4 (0 = "not a defect" — the veto). Severity = mean; findings averaging < 1 with any 0 votes are dropped as false positives and logged.
5. Findings whose verification another finding blocks get `unverifiable_due_to`, and appear under *Not assessed*, not as absent.
6. **Before discarding a vetoed finding, ask what it was reaching for.** A false positive whose *reasoning* was sound often marks a real condition with no entry in the taxonomy — the reviewer saw something, and named the nearest thing available. `elided-series` exists precisely because of a wrong finding: the claim ("this chart is missing data") was false, but the condition it implied (a chart can show fewer categories than it holds, and the reader cannot tell) had no name. Log rejections with a one-line note on whether they imply a missing defect; that log is the taxonomy's backlog.

**Verification is function-scoped, never file-scoped.** When checking whether a value, type, or branch is handled, ask whether *the specific consumer* handles it — not whether the file mentions it. A file-level grep is the single most reliable way to score a real defect as already-fixed, because the mentions that satisfy the grep are usually the halves somebody already corrected. See `eval/baseline.md` for the worked instance.

## Fixing (only when asked to fix)

Tier every confirmed finding:

- **Mechanical** — deterministic, convention-safe, one correct fix (use the design system's existing component, add the missing attribute, correct the heading level). Apply it. Then **re-run the full sweep on the touched surface** — the fixed defect must be gone AND no new defect introduced. Spot re-checking the one defect is insufficient; a real-but-incomplete fix passes a spot check.
- **Proposed** — a correct fix exists but requires choosing among alternatives. Emit a diff; do not apply.
- **Reported-only** — the fix depends on intent the audit cannot see. Report; suggest a `conventions.md` entry so the decision gets recorded either way.

The critic that found a defect never applies its fix; the agent that applied a fix never verifies it alone.

## Output

```
# Punch list — <surface> — <date>
Severity basis: <declared bases>
N defects (primaries) · M mechanical-fixed and re-verified · K proposed · J reported
## Findings          — table: defect · surface · symptom · evidence · severity · fix
## Convention overrides — findings suppressed by declared conventions
## Not assessed      — defects the input could not support, and why (including blocked scopes)
```

Counts are facts, never grades. There is no score.

## Taxonomy

`taxonomy/*.json` — entries validate against `schema/defect.schema.json`. Load all three categories for a full sweep; the `detectable_from` field decides what runs for the given input.
