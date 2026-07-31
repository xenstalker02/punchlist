# Failure case — a false positive from a rendered pass

**Why this file exists:** `screenshot-false-positives.md` records why the *screenshot* path needs guardrails. This is its counterpart, and the more uncomfortable one: the **rendered** pass — the tool's own answer to screenshot unreliability, the thing `source+rendered` detection is supposed to be grounded in — has its own systematic false positive, and it fails in the same alarming direction.

## What was reported, and what was true

An audit run measuring a live product in a browser reported that **`focus-within:opacity-100` was broken across every kebab menu in the app** — controls that are `opacity-0` until hovered were, it claimed, staying invisible when focused, leaving keyboard users tabbing onto controls they cannot see.

That is a real defect class and the reasoning was sound. It was also wrong.

The browser surface was **not compositing**: `document.visibilityState === "hidden"`, and zero `requestAnimationFrame` callbacks fired in 1.5 seconds. CSS transitions do not advance in that state. So `getComputedStyle` returned every transitioned property's **start value, permanently**. The opacity was pinned at 0 not because the rule failed but because the transition toward 1 never ran a single frame.

The finding survived until a deliberate **control** was run — the same class list on a component known to work returned the same frozen 0. One measurement, two elements, and the contradiction was immediate.

A second instance in the same run: hot module replacement produced a stale composite in which **two pages' `h1` elements were present simultaneously**, which would have scored as a duplicate-heading defect on a page that has exactly one.

## The class

**A rendered pass is only as trustworthy as the renderer's liveness, and liveness is not something the measurement reports.** `getComputedStyle` returns a number either way. There is no error, no warning, and no null — a frozen page and a live page are indistinguishable from the value alone.

The dangerous property is again the bias. A frozen renderer reports every animated affordance as sitting in its **pre-interaction** state: hidden things stay hidden, collapsed things stay collapsed, faded things stay faded. So the failure mode is a confident report that **interactive states do not work** — hover reveals, focus rings, expansions, streaming, materialization. That is the alarming direction, and it is precisely the surface a design audit is most often asked about.

Note the symmetry with the screenshot case: **both input paths fail toward false alarm rather than silence, and both do it by making an absence look like a defect.** For screenshots the absence is manufactured by the frame; here it is manufactured by time not passing.

## What changes as a result

1. **Liveness is a precondition, not an assumption.** Before any rendered measurement, assert the surface is compositing: `document.visibilityState === "visible"` **and** at least two `requestAnimationFrame` callbacks inside ~100ms. If either fails, the run reports `not-assessed` for every transitioned property rather than producing values.
2. **Never measure a transitioned property in its transitional window.** Either strip the transition (measure on a fresh node, or with the transition class removed) or wait for `transitionend`. A single `getComputedStyle` immediately after a state change is a race even on a healthy page.
3. **Any "this state does not work" finding requires a control** — an element of the same class known to work. A finding that a mechanism is broken *everywhere* is far more likely to be a broken harness than a product that shipped with the mechanism universally dead. Treat universality as evidence against the finding.
4. **Measure on fresh loads.** HMR composites are not the built product. Reload before recording evidence.

## The general rule this generalizes to

The existing guard says *when the input is a screenshot, absence is not evidence.* The rendered pass needs its sibling: **when the input is a live DOM, a value is not evidence that the value was produced.** A frozen renderer, a detached node, and a page mid-transition all yield readings that look exactly like measurements.

Both rules reduce to the same discipline the taxonomy already applies to products — a green result from a check never observed failing is not a result. The control is not optional rigour; in both documented cases the control is the entire difference between a finding and a fabrication.
