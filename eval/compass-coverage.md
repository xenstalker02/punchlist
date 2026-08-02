# Coverage test — Compass collections IA

**The question this answers:** the taxonomy was re-derived from scratch. Can it still name every defect a working audit actually found? A taxonomy that loses coverage in a rewrite is a worse instrument, however original.

**Corpus:** a production React app (pharma commercial analytics), collections information architecture. **Ground truth:** 15 findings from a read-only audit run against the predecessor taxonomy on 2026-07-30, each with a `file:line` location and rendered-DOM evidence. This is a *coverage* test, not a precision test — it asks whether the vocabulary is expressive enough, not whether a model detects reliably. Precision and recall require a detection run against a pinned commit and are not claimed here.

## Result: 15 / 15 named, after closing 2 gaps

| # | Defect found in the audit | Punchlist entry |
|---|---|---|
| F1 | Every saved insight invisible — lookup had branches for 3 types, none for the 4th, so cards silently dropped | `manifest-gap` |
| F2 | Count tallied parent groups where the user counts saved items; right by accident in 1 of 3 collections | `counted-in-crates` + `coincidental-concord` |
| F3 | Section structure computed and never displayed — the user had to remember collection contents | `recall-tax` ← **added by this test** |
| F4 | The remove picker was the only place to see what a collection held | `demolition-preview` ← **added by this test** |
| F5 | One concept as an 82px bare row in one place, a 408px rich card in another | `weight-whiplash` |
| F6 | Same three collections in two different orders on two surfaces | `order-drift` |
| F7 | Raw browser `window.confirm` in a fully themed dark app that has its own modal | `foreign-frame` |
| F8 | `No ${filter} in this collection yet` rendering as "No kbqs in this collection yet" | `backstage-bleed` |
| F9 | Modal header hardcoded while the same file computed the correct noun | `blank-doorplate` |
| F10 | Label and its count 1001px apart, the pairing duplicated 40px above | `long-distance-label` |
| F11 | 169 characters per line at 12px against a 65–75 target | `marathon-measure` |
| F12 | "0 items · Created 7/30/2026 · Latest data: 7/30/26" on an empty collection, two date formats | `phantom-freshness` |
| F13 | Nav items as bare divs — no role, tabindex, or current state; page unreachable by keyboard | `keyboard-dead-zone` |
| F14 | Filter pills with colour-only selection and no `aria-pressed` | `keyboard-dead-zone` |
| F15 | Heading order H1→H2→H4; group labels as spans, invisible to assistive tech | `painted-on-headings` |

## What the test earned

**Two defects exist because this ran.** `recall-tax` and `demolition-preview` were absent from the first draft — the re-derivation had covered the defects that leave visual evidence and quietly dropped the two that only appear when you walk the flow. Both are grounded in Nielsen's recognition-over-recall heuristic and Shneiderman's memory-load rule, so they were reachable from the standards alone; nobody reached them until a real audit demanded a name.

**Two findings share one entry.** F13 and F14 both resolve to `keyboard-dead-zone` — correctly, since one definition covers missing role, name, and state. Fifteen findings, fourteen distinct entries: the taxonomy is not padded to match the corpus.

**Six of the fifteen carried a second classification.** That is why a finding has one primary defect plus `also_matches`, and why headline counts are computed on primaries only.

## What this test does not show

- **Nothing about detection.** Every finding here was located by a human-directed audit. Whether Punchlist's own pipeline finds them, and at what false-positive rate, is the open question, and the one that matters.
- **Nothing about one-corpus generalization.** One app, one IA, one team's conventions. A second corpus with a different stack is needed before any claim about the taxonomy's completeness.
- **Behavior coverage is under-tested.** The audit was read-only and mostly static, so most `behavior` entries — which need interaction — were never exercised against it. Their grounding is the documented defect record from the same product's build sessions, not this run.
