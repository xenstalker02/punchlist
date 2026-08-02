# Detection eval — pinned baseline

The coverage test (`compass-coverage.md`) asked whether the taxonomy can *name* real defects. This is the harder question: does the pipeline **find** them, and how often does it invent things that aren't there? Coverage is a property of a vocabulary; precision is a property of a detector. Only the second one is a moat.

## The pin

**Corpus:** a production React app (pharma commercial analytics), collections information architecture.
**Baseline commit:** `79b5c2e` — *"fix(collections): the filter and the counts spoke different vocabularies"*.
**Why this commit:** the ground-truth audit ran read-only against exactly this tree. Scoring against any other commit measures a different product.
**Post-fix state:** `7dba296`, useful as a negative control — findings that legitimately disappear between the two are fixes, not detector misses.

**Ground truth:** the 15 findings in `compass-coverage.md`, each with a location and rendered-DOM evidence.

## The trap that will corrupt this eval if you let it

**Verifying finding F1 with a file-level grep produces a confident, wrong answer.** F1 is the render path silently dropping every saved insight, because a type lookup had branches for three types and not the fourth.

Verified against the baseline tree:

- `git grep -c insightSection` on `HomePage.tsx` at `79b5c2e` returns **6 hits**. A file-scoped check concludes the type is handled and scores F1 as a **false positive**.
- All six sit between lines 2110 and 2147 — the filter predicate, the "All" balancer, a top-3 slice, and comments. Those are the halves that commit fixed.
- `getItemDetails`, the render path, begins at line **2215** and contains **zero** references to it.

**So the check must be function-scoped, not file-scoped.** Ask whether the specific consumer handles the value, never whether the file mentions it.

That is not an eval quirk — it is the same shape as the defect. The fix that produced this baseline corrected the two measurable halves, verified both, and stopped; nobody followed the value to its last consumer. The fix is also what made the render defect *reachable*, since beforehand the insights filter matched nothing at all. **A fix can be correct, verified, and still leave the surface broken** — which is why `SKILL.md` requires re-verification by full re-sweep of the touched surface rather than re-checking the finding.

## Scoring rules

1. **Function-scoped verification.** Every ground-truth check names the consumer it must hold in. No file-level greps.
2. **Blind detection.** The detecting critics must not see `compass-coverage.md`. A detector shown its answer key measures nothing.
3. **Count primaries.** A finding matching two defects is one hit, scored on its primary.
4. **Score false positives separately and loudly.** Precision matters more than recall here: a tool that cries wolf gets uninstalled faster than one that misses. A false positive at the frame edge (see `screenshot-false-positives.md`) is a distinct failure mode and should be reported as its own rate.
5. **Report per-input-mode.** A screenshot run and a rendered run are different detectors and must never be pooled into one number.
6. **Publish the misses.** The defects the pipeline did not find are the honest part of the number, and the roadmap.

## Not yet run

No precision or recall figure is claimed anywhere in this repo. When one exists it belongs here, per-defect and per-input-mode, with the misses listed.
