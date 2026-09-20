# Queen Worm: keeping the portfolio and basket usable in a desktop-style interface

This owner-approved field report describes a Punchlist run on Queen Worm's local
portfolio and shop prototype. The project owner authorized publication of this
curated account on 10 September 2026. The source repository, raw audit records,
screenshots, and design file remain private and are not included or linked here.

The task was to enter the portfolio, browse a collection, inspect a photograph,
choose a sample print, and review or change the basket. The interface deliberately
uses overlapping desktop windows, a single active window on mobile, and a
grey, silver, oxblood, and pale-pink palette. Demonstration content and closed
checkout were declared boundaries, not defects to discover.

## Run identity and evidence limits

The canonical record is `queen-worm-public-preview-2026-09-09`, recorded at
2026-09-10T03:13:03Z, on the evening of 9 September in the project's local time.
It identifies the installed skill as version 0.1 and records the 50-entry
taxonomy. An exact installed-skill commit was not captured; this report does not
attribute the run to a pinned upstream revision.

The declared profile was **experience**. Severity was rated against **task
completion and comprehension within the public design preview**, with live
checkout and production content intentionally unavailable. Ratings below are
the original 0–4 ratings, not a new questionnaire or a product score.

One AI assistant performed the orientation, rendered measurements, interactions,
and severity assessment. That assistant had also helped implement the prototype.
Requester instructions restricted delegation during the audit. This was therefore
a **single-agent heuristic review**, not the intended independent multi-critic
protocol, independent user research, or a measurement of detection accuracy.

Evidence came from an unconfigured, logged-out local preview in Chromium, its
live DOM and computed styles, and supporting source inspection. Desktop, narrow
phone, and short landscape layouts were inspected. Image delays and rejected
storage writes were deliberately simulated in disposable browser contexts;
they were not incidents observed in production traffic.

The retained canonical audit, repair report, browser logs, and subsequent source
review support this account. Readers can inspect the reasoning and reproduce
the contrast arithmetic below, but cannot independently replay the private
application from this contribution. Historical observations are identified as
such; this is not a new audit of the current application.

## Findings along the journey

![Journey graph of the original Queen Worm audit: seven named findings cover hidden focus, low contrast, long lines, loading feedback, heading structure, persistence, and quantity-limit feedback; three dashed taxonomy gaps cover mobile basket layout, landscape fit, and focus after removal.](https://raw.githubusercontent.com/xenstalker02/punchlist/53c47eb168a17b83b90656d7f8c3dddb0f069419/assets/field-reports/queen-worm-findings.svg)

The graph is an authored summary, not a product screenshot or new evidence.
F1–F7 map to the primary findings below; G1–G3 map to the gap descriptions.
Shared focus and reading findings also affect later stages. Solid and dashed
borders distinguish findings from gaps without relying on color alone.
The [SVG source](https://raw.githubusercontent.com/xenstalker02/punchlist/53c47eb168a17b83b90656d7f8c3dddb0f069419/assets/field-reports/queen-worm-findings.svg) retains editable
text and the canonical finding/gap IDs.

## Findings and the later repair

The original bundle contains **seven primary findings and three taxonomy gaps**.
Its finding lifecycles remain **open, reported-only** as the historical record.
The separate, later repair report marks those same finding and gap IDs fixed.
The repair column below summarizes that later work rather than rewriting the
original audit's status.

| Finding ID and primary defect | Original rating | Observed problem | Later repair |
| --- | --- | --- | --- |
| F1 · `f-4914391b09d2` — `keyboard-dead-zone` | 3/4 | Tab and reverse Tab reached homepage links fully covered by an open mobile window. | Covered header/navigation become inert; the active window and visible taskbar remain operable. Closing and resizing restore useful focus. |
| F2 · `f-0009746bbf55` — `vanishing-ink` | 2/4 | Small prices, photo credits, basket variants, and preview notices had insufficient contrast on their rendered surfaces. | A darker shared secondary-text token replaces the affected overrides; rendered pairs were rechecked. |
| F3 · `f-3391dd362497` — `silent-stall` | 2/4 | A held full-size image request left a blank photograph area while its title and print controls were already present. | A retained thumbnail and loading message precede decoding; failures expose a retry action. |
| F4 · `f-3c12fcc4d317` — `amnesiac-relaunch` | 2/4 | Under a simulated storage-write failure, normal add feedback appeared, but refreshing discarded the basket without warning. | Failed persistence produces a persistent temporary-basket notice while unsaved items remain. |
| F5 · `f-2f15498d4644` — `celebrated-no-op` | 1/4 | At the 99-copy limit, another addition left quantity unchanged but repeated the success toast. | The operation returns an explicit outcome; a refused addition produces limit feedback. |
| F6 · `f-8c45d9b7abdd` — `marathon-measure` | 1/4 | Supporting paragraphs produced long rendered lines at small text sizes. | Paragraph widths are constrained and actual wrapping is checked in the browser. |
| F7 · `f-2107a1268d08` — `painted-on-headings` | 1/4 | The photograph view exposed the site h1 followed directly by the photograph's h3, with no h2 section heading. | The photograph title becomes an h2 while retaining its appearance. |

The storage finding also names `ventriloquist-confirmation` as a secondary match.
It remains one finding: the misleading confirmation and lost basket came from
the same failed-persistence condition. A count of matched taxonomy entries would
therefore differ from the count of primary findings.

## What established the important failures

**Focus was present but hidden.** The audit read the active element during both
Tab directions and checked its rendered position and occlusion. Homepage controls
received focus underneath the mobile window. The failure was not inferred from
the existence of a keyboard handler or from a screenshot without a focus ring.

**Secondary text had measurable contrast loss.** The following opaque pairs were
recorded from computed styles and their rendered backgrounds. Ratios are rounded
for display and can be recalculated from the included sRGB values using WCAG
relative luminance and `(lighter + 0.05) / (darker + 0.05)`.

| Text | Foreground | Background | Recorded ratio |
| --- | --- | --- | --- |
| Shop prices | `#7e6670` | `#e7e2da` | 4.05:1 |
| Photograph credits | `#706167` | `#cec9c1` | 3.55:1 |
| Basket variants | `#7f6e72` | `#e7e2da` | 3.72:1 |
| Preview attribution | `#8b787a` | `#e7e2da` | 3.22:1 |

These were ordinary small text, below the applicable 4.5:1 minimum. Invisible
announcers, decorative glyphs, inactive controls, and uncertain photographic
backgrounds were excluded from this measurement. This is evidence about the
listed samples, not a blanket accessibility verdict.
See [WCAG's contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).

**The fault tests isolated specific boundaries.** Holding only the full-size
photograph response left the image incomplete, with zero natural width and no
loading text; releasing it displayed the photograph. Separately, making the
storage write throw `QuotaExceededError` let the basket appear to accept a print,
then lose it on reload. Normal stored baskets survived reload. The latter finding
was conditional on the simulated failure, not a claim that persistence always
failed.

**Refusal needed its own feedback.** The original cap probe used the public add
control to reach 99 copies, let the existing toast expire, then attempted another
addition. Both the visible and stored quantities stayed unchanged while a fresh
success message appeared. An accurate destination count did not make that
confirmation accurate.

For text measure, the audit grouped character-level DOM Range rectangles into
rendered lines. It did not substitute viewport width for line length. For heading
structure, it inspected the headings exposed by direct photograph views and
compared them with the correctly structured collection grid.

## Real conditions that did not fit a taxonomy entry

These remain named **gaps**, not additional Punchlist defect definitions or
automatic requests to broaden existing entries.

- **G1 · `g-mobile-basket-layout`:** the phone basket squeezed the title and variant
  beside a wide quantity-control group. Rendered rectangles and text wrapping
  established the problem. The repair gives the information the available width
  beside the thumbnail and moves quantity and line price to a separate row.
- **G2 · `g-landscape-window-fit`:** the initial short landscape window extended below
  the taskbar. Scrolling its contents still left controls covered; moving or
  maximising the window could recover them. The repair fits window placement and
  height to the available viewport, with independently scrolling print options.
- **G3 · `g-basket-removal-focus`:** after keyboard removal of a basket line, the audit
  waited two animation frames and observed focus on `BODY`, including when other
  lines remained. The repair focuses the next remaining Remove control, the
  previous final item, or the empty-basket recovery link.

The removal case resembled `dropped-baton`, but that entry's definition addressed
overlay completion. Recording the mismatch preserved a real observation without
claiming that the nearest available name was an exact fit.

## Rejections that improved the report

- **Apparently missing scrollbars:** rerunning with native Chromium scrollbars
  enabled showed the scrollbar. Playwright's default suppression had created the
  appearance. The observation was rejected, with no taxonomy gap.
- **Every small target fails:** checking spacing and equivalent-function
  exceptions disproved the blanket claim about small credit and footer links.
  This did not establish that every target in the product was compliant.
- **Closed checkout and empty future categories are broken:** both were declared
  preview boundaries and visibly disclosed. They were convention overrides.
- **An uncommitted print choice resets after leaving:** the reset was reproduced,
  but committed basket variants remained correct. Draft-selection preservation
  was not established as a requirement for this journey, so it did not become a
  lead finding. That decision should be revisited if comparison becomes a task.

The portfolio entry, complete photographs in the normal viewer, ordinary basket
consistency, filters, direct links, and motion controls also supported the task.
These strengths provide context; they do not cancel the failures above.

## What the follow-up establishes

The owner later authorized repairs to the seven findings and three gaps. Focused
browser regressions covered forward/reverse keyboard navigation, removal focus,
quantity refusal, simulated storage failure, delayed and failed image loading,
retry, stale image completion, narrow basket layout, and short landscape windows.
Rendered contrast and paragraph measurements accompanied those checks.

Lint, type checks, unit tests, the browser suite, and the production build passed
before the changes were merged into the project's default branch. The existing
upstream bundling warnings remained. Corresponding desktop, mobile, and feedback
states were also updated and compared in the editable design handbook.

A separate AI subagent reviewed the broader change set's source before merge and
reported no supported regressions. That was an independent **source review**, not
an independent browser re-sweep of this audit, a multi-rater severity exercise,
or human ground truth. The implementing assistant performed the browser repair
verification. This report does not claim full compliance with Punchlist's
independent fix/re-sweep protocol or verify a production deployment.

The original run could not assess changing live catalog configurations,
checkout/admin operations, physical mobile devices, other browser engines,
actual screen-reader sessions, or human task performance. In particular, a fixed
folder count matched the only available static catalog; hypothetical catalog
changes were recorded as not assessed rather than as a confirmed wrong count.

For Punchlist, the useful lessons are to measure focus after the interaction,
separate accepted in-memory work from durable storage, tie feedback to the actual
operation result, and challenge automation artifacts before changing the product.
The taxonomy gaps are candidates for further evidence, not proof that three new
definitions are needed. A useful next independent check is the repaired journey
with a keyboard or mobile screen-reader user on target hardware.

No conversion, prevalence, time-saving, defect-recall, overall accuracy,
production reliability, or blanket standards-compliance claim is made.
