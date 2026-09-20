# Angel’s Rest: keeping a print configuration visible through cart review

This owner-authorized field report documents the print-shopping journey on
[Angel’s Rest](https://www.angelsrest.online), its audit findings, and the
independently verified local repairs.

The task is to choose a print configuration, inspect it in the cart, and return
to the product to verify the selection before purchase. When two frame choices
cost the same, the price cannot identify which frame the shopper selected.

## Evidence and status

The private source records are the original canonical audit (`audit.json`), the
repair handoff (`before-after.md`), and the separate post-repair re-sweep
(`after-audit.json`). They record live, logged-out browser observations and
local repair verification. Raw evidence, screenshots and project source remain
private; this report is an attributed account, not a self-contained reproduction.

The historical audit retains its **open, reported-only** statuses. The separate
re-sweep identifies those same finding IDs as verified fixed. Ratings below are
the original ratings against **task completion and confident purchase decisions**.

| Original finding | Recorded before evidence | Separate local verification |
| --- | --- | --- |
| `f-8a112c7bbdcb` — `recall-tax`, **3/4** | Stored frame identities differed, but both cart views and review destinations omitted the saved choice. | Exact frames are visible; review links restore the configuration and close the drawer. |
| `f-95a7d94abbd6` — `amnesiac-relaunch`, **1/4** | Reload discarded an unfinished configuration. | Valid selections survive reload, review, reused routes and back/forward. |
| `f-9c595b2fd898` — `celebrated-no-op`, **1/4** | Capped additions ran normal feedback without increasing quantity. | Increment disables at the cap; another Add explains the refusal without success feedback. |

## The cart retained the choice but did not communicate it

Browser interactions directly established that two equal-price variants retained
different frame values while both cart views said only “framed.” Rendered and
accessibility inspection confirmed an omission rather than clipped text.
Following either review link reopened the default configuration, preventing
verification through that path too. This supports `recall-tax`; the navigation
loss is not assigned a separate approximate taxonomy label.

The repair uses the catalog’s exact frame label in the shared cart-line component
and lets details wrap. Browser re-checks verified frame width/color in both views
and restoration of saved material, size, border and frame after review navigation.
Only available options are restored. Following a drawer link closes the overlay
so the destination can be inspected.

## Reload also discarded an unfinished configuration

Reload returned a configured print to default material, size and border choices
on both tested device sizes. Configurations already in the cart survived; the
lost work was the uncommitted selection.

The repair makes the product route’s URL own its reloadable selection, validates
option availability, and keeps embedded product instances independent. Browser
verification covered reload, review navigation, reused routes and back/forward,
including unavailable query choices.

## A refused addition still ran normal cart feedback

Beyond the 20-copy line limit, quantity stayed at 20 but the drawer opened
normally; mobile also ran its cart-droplet animation. No limit or refusal was
explained. The destination quantity was accurate and there was no textual
success toast, but normal addition feedback still ran after refusal.

The mutation now returns the actual quantity increase. A zero increase produces
a limit explanation and “nothing was added” feedback without the addition
animation. Increment disables at the shared limit. Browser re-checks confirmed
these outcomes and unchanged quantities and totals after refusal.

## What verification establishes

Three independent AI critics re-checked the touched surfaces using Chromium at
1440×1000 and 390×844, light/dark themes, normal/reduced motion and labeled
synthetic adverse branches. Their completed browser observations and canonical
re-sweep record all three findings above as verified fixed. AI reviewer agreement
is not independent human ground truth.

The handoff records the **same 26 regression cases** changing from **4 passing /
22 failing** on the original code to **26 passing** after repair. This set covers
the broader batch, including navigation, descriptions and focus. These are
historical results, not a fresh run for this contribution.

The status is **locally repaired and independently browser-verified**. The
production audit and local re-sweep do not establish a controlled production
A/B comparison or verify deployment. The component comparison used invented data
inside real project components; its evidence also remains private. Any upstream
synthetic example needs independently authored material and new evidence.

## Limits and lesson

Original detail-state coverage was limited to one portfolio and one print
product. Checkout, payment, forms, private galleries, accounts and backend
operations were excluded. Physical mobile devices, Safari and actual
screen-reader sessions were not tested.

The re-sweep retained two unchanged secondary contrast findings: footer text at
about 3.33:1 in light and 3.92–4.10:1 in dark samples, and the full-page empty-cart
message at about 3.80:1 in the final light sample. These remain separate follow-ups.
Measurements sample specific theme/time states, not every palette or animation
frame.

The owner intentionally kept the liquid mobile navigation focus ring absent.
The temporary ring change and its tests were removed; functional focus restoration
remained fixed and verified. That rejected treatment is not unfinished
implementation or a waiver of the measured accessibility limitations.

For Punchlist, the lesson is to inspect every place a shopper can review stored
configuration, including what review links actually restore. An accurate cart
can still be difficult to verify when summaries omit distinctions. At a quantity
limit, feedback should follow the mutation’s outcome.

This field report makes no conversion, time-saving, defect-recall, overall
accuracy or blanket standards-compliance claim.
