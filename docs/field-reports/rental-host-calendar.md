# Rental-host calendar: counts, keyboard recovery and pending work

This requester-authorized field report describes a Punchlist run on a rental-host
development interface. It is a curated account, not publication of the private
application or its raw audit. The source repository, deployment addresses,
screenshots, local evidence paths and account information are omitted. Booking
records used in the audit were synthetic. No real guest records or provider
operations were inspected.

The repair workflow requires independent re-sweeps, CI and a separately verified
development deployment. This report is not a launch-readiness declaration.

## Task, protocol and limits

The host needed to identify a property and dates, inspect a booking, review a
nightly-price change, and understand the result. The declared profile was
**experience**; severity meant **task completion, confidence and recovery in the
currently supported development calendar**. Future integrations were explicit
boundaries rather than missing features to score.

The initial audit was recorded on 5 November 2026 using an installed Punchlist
identified as `0.1.0+installed`, taxonomy `0.1.0`, schema `1.0`. An upstream commit
was not captured; this report does not retroactively pin the run to the current
upstream revision.

Three independent AI critics covered Interface, Content and Behavior. Each closed
its assigned eligibility rows before the merged observations returned to all
three for severity ratings. The ledger covered 50 eligible entries: 20 Interface,
16 Content and 14 Behavior. Desktop, phone and small-phone layouts were inspected
in light and dark themes. Rendered DOM, computed styles, interaction and source
evidence had distinct roles. Chromium supplied the main walkthrough; Firefox and
Linux WebKit supplied focused cross-checks.

The initial result contained **eight primary findings and one taxonomy gap**.
A later repair re-sweep found a second gap. The tables below preserve that
chronology. Ratings are the original 0–4 questionnaire means, not a product score.
Raw evidence remains private: readers can follow the reasoning and count the
listed records, but cannot replay the private application from this contribution.

## Findings and repair directions

| Stable ID and primary defect | Original rating | Observed problem | Repair direction |
| --- | --- | --- | --- |
| `f-0cd322d765bd` · `parallax-count` | 2/4 | Status badges counted the whole dataset while the list applied property and search filters. A badge could promise one booking while the result list showed none. | Derive badges and results from the same property/search scope, then apply the selected status to the list. |
| `f-522efab4e919` · `dropped-baton` | 2/4 | Closing or saving an editor opened by a long-press left focus on BODY; the next Tab restarted at Skip to content. A previously inspected detail caller could also disappear when another date range was selected. | Establish a persistent selected-day control as the gesture caller before opening the editor; verify completion paths and caller connectivity. |
| `f-8e6bf51c2ff4` · `silent-stall` | 2/4 | Holding the calendar navigation response left the old bookings page unchanged without visible or accessible pending feedback. Releasing that response completed navigation. | Show operation-bound destination feedback outside document flow and mark the content busy; clear it on completion or error. |
| `f-a8e17b972e07` · `guessing-game-field` | 1/4 | Search relied on placeholder text, which disappeared after typing. | Keep a persistent visible label associated with the input. |
| `f-71b88811f647` · `painted-on-headings` | 1/4 | The page h1 and month h2 were followed by calendar event h4 elements, although events were individual labels rather than document sections. | Render escaped event labels without inventing heading sections; retain appearance and activation. |
| `f-adc25bbb71ec` · `patchwork-voice` | 1/4 | Valid one-guest and one-night branches produced plural wording. | Correct singular nouns and exercise valid controlled branches. |
| `f-e95efcf936f3` · `sub-floor-target` | 1/4 | A standalone preview link had an approximately 21px continuous hit band. At small width its inline fragments needed separate hit testing. | Give the link a continuous control-sized target while preserving wording and wrapping. |
| `f-72408d5cb445` · `marathon-measure` | 1/4 | Supporting desktop notes produced lines of 91 and 100 actual characters at small type sizes. | Constrain those notes and measure their resulting rendered lines rather than trusting a CSS unit. |

The singular-copy fixture used a one-guest stay of a permitted multi-night length
and a one-night owner block. It did not establish or change a one-night guest
booking policy. The target observation did not establish a WCAG 2.5.8 violation:
spacing and its exceptions needed to remain distinct from the footprint finding.

## Two focus conditions that needed separate gap records

**G1 · `g-internal-step-focus` — observed in the initial audit.** Review and Back
replaced the focused control while the editor stayed open. Reaching the final
review page disabled the focused Next button. Focus fell to BODY and the modal
trap recovered at Close, losing the task position. This was not overlay-close
restoration, so broadening `dropped-baton` to absorb it would obscure the condition.

The repair gave the labelled review region a deliberate focus handoff and
returned Back to the retained price draft. The full re-sweep then exposed a
responsive variant: enlarged text created small review pages; restoring desktop
geometry remapped the penultimate page onto the final page and disabled its
focused pager. That variant required the same recovery during layout remapping,
while preserving intentional focus on a global notice or Close control.

**G2 · `g-event-enter-activation` — discovered during the repair loop.** Enter on
a calendar event opened its details, then the same keydown's default action
clicked the newly focused Close button before keyup. Space worked, and focus
returned to the correct, connected event caller. A final active-element check
alone therefore looked healthy even though the destination immediately vanished.

Two critics independently captured the event sequence on both the repair branch
and the previously deployed version. That comparison established a pre-existing
condition rather than a regression from the heading change. Missing keyboard
reachability and failed close restoration were both imprecise labels for it.
The handled activation now cancels that browser default. Enter, Space and pointer
regressions verify the retained dialog and connected return caller across engines.

Neither gap is counted as an additional taxonomy defect or silently added to the
initial eight findings. The separate repair record closes those eight findings and
both gap IDs after independent rechecks and verification on the dedicated
development deployment.

## Probes that changed the conclusion

**Cross-filter identity mattered.** The default booking view looked consistent.
Property, search and status combinations exposed the mismatch between badge scope
and list scope. Comparing visible records with their shared identity was more
useful than checking isolated totals.

**Caller and event sequence mattered.** Keyboard date selection passed while
long-press selection failed. All close/save paths, a removed temporary caller,
and the internal review transitions needed separate probes. For the later Enter
gap, keydown, default click and keyup explained a failure that a handler's presence
or correct final focus could not establish.

**Actual text lines mattered.** A note already constrained to `70ch` still rendered
91 characters on its first line. Character-level DOM Range rectangles exposed
the real line lengths. The local repair measured 70 and 68 characters on the
corresponding desktop lines; this is a retained run observation, not a universal
width prescription for other fonts or languages.

**Faults needed honest labels.** A deliberately held route response established
pending navigation; a controlled route-data error established clearance and
recovery. These were synthetic fault probes, not production incidents. Compiled
component fixtures covered delayed responses, teardown and private-caller
busy/inert ordering without supplying a private session or writing backend data.

## What the workflow caught, and what its evidence did not prove

One footer-order observation was vetoed because it did not harm the declared
task. It remained a rejection rather than inflating the repair list. Browser
validation wording was distinguished from app-authored copy; a low-year error
message remained a noncounted implementation observation.

Probe mistakes also needed correction. A screenshot taken during a transition
showed stale visual state until compositing settled. A long-press beginning near
the viewport edge triggered calendar auto-scroll; fresh, hit-checked coordinates
separated that behavior from the intended range-selection probe. Full-page
screenshots could change scroll position, so geometry comparisons needed the
actual document coordinates after capture. None became product findings.

The generated HTML report also overflowed long fingerprint strings at a phone
width, while its Markdown projection remained readable. That is renderer
feedback, separate from a finding about the inspected application. The installed
skill was not patched as part of application repair.

The repair loop required scoped commits, independent re-sweeps, CI and a dedicated
development deployment. Those checks do not establish physical iPhone
keyboard/zoom behavior, authenticated persistence, provider integration, guest
website readiness or production launch. The second gap found during re-sweep is
also a concrete reminder that a closed eligibility ledger is a record of its
probes, not proof that every reachable condition was exhausted.

## Upstream feedback

The useful extension points are precise internal-step focus conditions and
keyboard activation that destroys its own destination. This report supplies
observations for taxonomy discussion; it does not add definitions, change
scoring, or broaden existing entries.

Future evaluator guidance could call out full activation sequences alongside
caller/connectivity checks, and distinguish settled viewport geometry from
capture-induced scrolling. The long-fingerprint rendering issue deserves a
separate renderer reproduction. No precision, recall, prevalence, time-saved or
general accessibility-certification claim follows from this case.
