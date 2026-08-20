---
name: punchlist
description: Named-defect design audit. Use when asked to review, audit, or critique a UI, screen, flow, or product surface — or when asked "what's wrong with this design". Runs an enumerable defect taxonomy (Interface · Content · Behavior) through independent critics with post-merge severity rating, returns findings as data with locations and evidence, and applies mechanical fixes verified by re-sweep. Not for generating new designs.
---

# Punchlist — the named-defect design audit

You are running a punch-list inspection, not writing a review. The canonical output is a list of **named defects, each with a location, evidence, and a required fix** — never unsupported impressions. A human-facing report may tell the story of a task, but every problem it presents must trace back to a verified finding or an explicitly labeled taxonomy gap. If a defect from the taxonomy is not present, it does not appear. If the input cannot support a check, say so in *Not assessed* — never guess.

## Inputs, in order of preference

1. **Live rendered app** (browser/Playwright available) — full taxonomy. Source reading alone is FORBIDDEN for interface/behavior checks: dead CSS, cascade losses and unfired branches are invisible in source. Read computed styles and the live DOM. **A value is not evidence that the value was produced.** Assert the surface is compositing before measuring anything transitioned, and treat a mechanism that appears broken *everywhere* as evidence against the finding rather than for it.
2. **Screenshot(s)** — run only defects whose `detectable_from` includes `screenshot` or `content-text`. List every skipped defect under *Not assessed*. Obey the frame rules below; they are not optional.
3. **Figma** (MCP available) — as screenshots, plus structural reads where the API provides them.

### When the input is a screenshot, absence is not evidence

A frame can manufacture every one of these: a sentence that stops mid-word, a chart missing most of its categories, a control that isn't there, a list that appears to end. **An image cannot distinguish content the product truncated from content the frame cut, nor data the product omitted from labels the chart library elided.** Both readings look identical in pixels — and the wrong one is always the more alarming one, so a screenshot auditor is biased toward false alarms rather than toward silence. That is the expensive direction: it spends the user's trust on the first run.

Rules:

- **Distrust your own edges.** If the evidence for a finding sits within ~24px of the image boundary, do not report it as a defect. Route it to canonical Not assessed with a frame-limited blocker and a concrete question for a rendered pass to answer.
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

### Preflight: authority, target, and privacy

Classify the target before opening it or collecting evidence:

- **Public** is the default. Work from public, logged-out access unless the brief explicitly says otherwise.
- **Authorized-restricted** requires the requester's explicit, current authorization to inspect that target. Keep evidence and outputs restricted by default; do not copy, attach, publish, or render it for a recipient until the requester separately approves publication.
- **Synthetic** is invented or reproducible fixture evidence. Label it synthetic; never present it as an observation from a real product.

Record the target classification, source provenance, and what each available surface can prove. Before a recipient-facing projection, remove or redact local paths, credentials, private URLs, personal emails, customer identifiers, and screenshots without explicit publication approval and useful alt text. A redaction review is a required attestation, not a claim that the target itself is public.

## Before the sweep

1. Read the project's `conventions.md` if present. A finding that contradicts a declared convention is recorded under *Convention overrides*, not as a defect.
2. Write a one-sentence **evaluation brief** before inspecting. It must name the user, task, entry point, state/device, and output profile. Example: "A `[user]`, in `[state]` on `[device]`, starts at `[entry point]` and tries to `[complete task]`; `[profile]` profile. Severity basis: `[basis]`."
3. Choose an **output profile**:
   - `experience` — the default for a screen, flow, product, or unspecified UX audit. Prioritize task progress, mental models, decision support, feedback, trust, and recovery. Implementation evidence supports the finding; it does not become the story by itself.
   - `implementation` — use for an explicit accessibility, code, conformance, or design-system QA request. Prioritize operability, semantics, rendered measurements, and source-to-output failures.
4. Declare the audit's **severity basis** (e.g. "absolute usability", "task completion", "demo readiness") — before any finding exists. All severity ratings score against the declared bases only.
5. **Orientation pass**: complete the declared task once to understand the product's model and note what already supports the task. No flagging during orientation. Positive evidence may appear in the human report, but it is not scored and does not cancel a defect.
6. **Build the eligibility ledger before any critic starts.** Declare the atomic supported inputs (for example `screenshot`, `source`, `rendered`, or `interaction`), then list every taxonomy entry with at least one satisfied `detectable_from` route. A compound route such as `source+rendered` is eligible only when both atomic inputs are supported. Assign every eligible entry to at least one critic. Every row records nonempty eligibility evidence, a probe, closure evidence, and ends as `found`, `checked_absent`, or `not_assessed`; no eligible entry may disappear because no critic happened to remember it. `checked_absent` requires the actual probe and negative evidence, not “did not notice.” `not_assessed` is allowed only when the available input cannot support the probe or a named finding/dependency blocks it. Time, token budget, critic scope, and “not completed before freeze” are not valid reasons: reassign the row and continue. The ledger is evaluation evidence, not a user-facing defect dump.

## The sweep (evaluator pipeline)

Modeled on the heuristic-evaluation protocol (Nielsen): evaluators are independent, severity comes after merge.

1. **3–5 independent critics** (subagents), each briefed with: the evaluation brief, output profile, taxonomy, product/domain context, conventions file, a distinct lens, and the subset of eligible ledger rows they own. For an experience profile, choose from first-use task walkthrough · mental model and language · comparison and decision support · trust, state, and recovery · keyboard/accessibility. For an implementation profile, choose from rendered integrity · state/persistence · content accuracy · keyboard-only operation · semantic structure. Critics never see each other's findings. Critics never saw the code they'd be grading being written (maker ≠ checker).
2. Each critic returns findings as the pre-merge subset of `schema/finding.schema.json`: primary `defect`, `surface`, `symptom`, `evidence`, `verified_how`. It also closes every assigned ledger row with `found`, `checked_absent`, or `not_assessed`, naming the probe and closure evidence. No severity yet, so findings at this stage do not validate against the final schema and are not meant to. Findings validate once step 4 has assigned severity.
3. **Coverage closure and merge**: fail the sweep if any eligible ledger row is missing a disposition, or if an input-supported row is marked `not_assessed` without a named blocker. Reassign incomplete rows before merge. Then deduplicate findings by defect + surface; genuine one-instance-two-defects cases use `also_matches`, one row. A complete ledger is not a claim that every defect was detectable; it is proof that silent omission did not masquerade as absence.
4. **Severity questionnaire**: the merged list goes back to every critic; each rates every finding 0–4 (0 = "not a defect" — the veto). Severity = mean; findings averaging < 1 with any 0 votes are dropped as false positives and logged.
5. Findings whose verification another finding blocks get `unverifiable_due_to`, and appear under *Not assessed*, not as absent.
6. **Before discarding a vetoed finding, ask what it was reaching for.** A false positive whose *reasoning* was sound often marks a real condition with no entry in the taxonomy — the reviewer saw something, and named the nearest thing available. `elided-series` exists precisely because of a wrong finding: the claim ("this chart is missing data") was false, but the condition it implied (a chart can show fewer categories than it holds, and the reader cannot tell) had no name. Log rejections with a one-line note on whether they imply a missing defect; that log is the taxonomy's backlog.

### Evidence-family probes

The ledger makes omissions visible; these probes keep a critic from “checking” an entry with an impression.

| Evidence family | Minimum probe |
|---|---|
| Container contents, recall, and destructive-only visibility | Inventory every place contents can be inspected before activating remove/delete. Compare retained/computed structure with what each non-destructive surface renders. |
| Cross-surface consistency | Build an identity map for every shared object class and fragment concept across surfaces; also compare sibling object classes that the product presents as parallel results of the same action or vocabulary. Compare order, label, interaction, footprint, and information richness. One convenient matching entity cannot close the entry, and a large difference closes cleanly only when the interface provides a visible hierarchy reason. |
| Templated content | Render every reachable branch, creating safe disposable runtime state when seeded data does not exercise one. Compare visible acronyms, nouns, counts, and labels with the canonical display value already computed or stored; a source template alone cannot prove its rendered output. If reaching a branch would require destructive or unavailable mutation, name that blocker instead of treating seeded coverage as complete. |
| Spatial association and text measure | Read rendered bounding rectangles for label/value pairs and duplicates. Measure font size and actual characters per rendered line (or line boxes); viewport width alone is not evidence. |
| Overlay completion and focus restoration | Record the exact caller, opener identity, selected-item count, destination, and close path. After close, wait two animation frames and read `document.activeElement`, connectivity, and accessible name. Never generalize a pass or failure from one caller to another. |

An eligible entry is `checked_absent` only after its evidence-family probe passes on every in-scope state or surface named by the brief.

### Experience-profile eligibility gate

Before rating severity, test every merged observation against the declared task:

- Name the **moment in the journey** and the **user-visible symptom**. If neither can be stated, it is not a lead experience finding.
- A task-independent standards failure may still qualify when it creates meaningful access, comprehension, control, or trust harm. State that harm plainly.
- Source, DOM, or semantic evidence proves a finding; it does not automatically make the finding important to this task. Put useful repair work without a material task effect in a secondary implementation appendix.
- If the user-visible condition is real but no taxonomy definition fits precisely, label it **Taxonomy gap**. Do not force-map it to the nearest defect. A taxonomy gap can appear in a human report as an observed opportunity, but it is not counted as a Punchlist defect until a new entry satisfies the repository's evidence rules.

**Verification is function-scoped, never file-scoped.** When checking whether a value, type, or branch is handled, ask whether *the specific consumer* handles it — not whether the file mentions it. A file-level grep is a reliable way to score a real defect as already fixed when the matches come from adjacent consumers rather than the consumer under review.

## Fixing (only when asked to fix)

Tier every confirmed finding:

- **Mechanical** — deterministic, convention-safe, one correct fix (use the design system's existing component, add the missing attribute, correct the heading level). Apply it. Then **re-run the full sweep on the touched surface** — the fixed defect must be gone AND no new defect introduced. Spot re-checking the one defect is insufficient; a real-but-incomplete fix passes a spot check.
- **Proposed** — a correct fix exists but requires choosing among alternatives. Emit a diff; do not apply.
- **Reported-only** — the fix depends on intent the audit cannot see. Report; suggest a `conventions.md` entry so the decision gets recorded either way.

The critic that found a defect never applies its fix; the agent that applied a fix never verifies it alone.

## Output

Punchlist produces two compatible layers:

1. **Canonical audit bundle** — the checkable record used for merge, severity, fixes, and re-sweeps. It records the brief, target classification, provenance, capabilities, critic assignments, eligibility ledger, final findings, gaps, not-assessed records, and redaction status. Validate it against the audit contract before use.
2. **Recipient projection** — an optional human view that references canonical finding, gap, and not-assessed IDs; it does not invent counts or duplicate evidence. Its publication classification must match the canonical target, and restricted projections require publication approval.
3. **Rendered report** — render only the validated canonical bundle plus validated recipient projection and bounded theme. Re-render from those inputs and compare the generated artifact before committing it; never hand-edit a rendered report.

For an experience profile, use `templates/experience-review.md`. Lead with the task and the decision that became difficult; translate named defects into plain-language headlines; keep technical proof adjacent but subordinate. Include what held up, limits, and the next user test. Do not present a raw defect count as a product verdict.

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
