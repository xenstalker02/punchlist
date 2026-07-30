---
name: punchlist
description: Named-defect design audit. Use when asked to review, audit, or critique a UI, screen, flow, or product surface — or when asked "what's wrong with this design". Runs an enumerable defect taxonomy (Interface · Content · Behavior) through independent critics with post-merge severity rating, returns findings as data with locations and evidence, and applies mechanical fixes verified by re-sweep. Not for generating new designs.
---

# Punchlist — the named-defect design audit

You are running a punch-list inspection, not writing a review. The output is a list of **named defects, each with a location, evidence, and a required fix** — never prose impressions. If a defect from the taxonomy is not present, it does not appear. If the input cannot support a check, say so in *Not assessed* — never guess.

## Inputs, in order of preference

1. **Live rendered app** (browser/Playwright available) — full taxonomy. Source reading alone is FORBIDDEN for interface/behavior checks: dead CSS, cascade losses and unfired branches are invisible in source. Read computed styles and the live DOM.
2. **Screenshot(s)** — run only defects whose `detectable_from` includes `screenshot` or `content-text`. List every skipped defect under *Not assessed*.
3. **Figma** (MCP available) — as screenshots, plus structural reads where the API provides them.

## Before the sweep

1. Read the project's `conventions.md` if present. A finding that contradicts a declared convention is recorded under *Convention overrides*, not as a defect.
2. Declare the audit's **severity basis** (e.g. "absolute usability", "demo readiness") — before any finding exists. All severity ratings score against the declared bases only.
3. **Orientation pass**: walk the surface once to understand what it is for. No flagging during orientation.

## The sweep (evaluator pipeline)

Modeled on the heuristic-evaluation protocol (Nielsen): evaluators are independent, severity comes after merge.

1. **3–5 independent critics** (subagents), each briefed with: the taxonomy, the product/domain context, the conventions file, and a distinct lens (e.g. first-use walkthrough · state/persistence prober · content reader · keyboard-only operator). Critics never see each other's findings. Critics never saw the code they'd be grading being written (maker ≠ checker).
2. Each critic returns findings in `schema/finding.schema.json` shape: primary `defect`, `surface`, `symptom`, `evidence`, `verified_how`. No severity yet.
3. **Merge**: deduplicate by defect + surface; genuine one-instance-two-defects cases use `also_matches`, one row.
4. **Severity questionnaire**: the merged list goes back to every critic; each rates every finding 0–4 (0 = "not a defect" — the veto). Severity = mean; findings averaging < 1 with any 0 votes are dropped as false positives and logged.
5. Findings whose verification another finding blocks get `unverifiable_due_to`, and appear under *Not assessed*, not as absent.

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
