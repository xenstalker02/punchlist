# Figma cover/report alignment

Use this handoff only for the public Punchlist cover and social preview. It does not authorize use of an audit, customer, employer, or other private-company material.

The project owner supplies the approved Figma frame URL directly when this handoff is run; do not commit a private collaboration URL to the public repository. The repository sources are `assets/social-preview.svg` and `assets/social-preview.png`. Align them with the committed synthetic report at `examples/synthetic/report.html` and `examples/synthetic/report.pdf`; the source theme is `themes/punchlist-default.json` and the report treatment is `templates/report/report.css`.

## Alignment target

- Keep the frame at 1280 x 640. Preserve a clear safe area within that frame; no text, logo, rule, or evidence frame should feel pinned to an edge or rely on cropping for legibility.
- Use soft white `#FFFFFF` as the canvas, rich ink `#10233D` for primary type and strong rules, muted `#526273` for secondary metadata, sapphire `#2457D6` for active emphasis, supporting violet `#7353BA` only as a supporting tone, evidence background `#F1F5F9`, and evidence label `#16324F`. Keep contrast and the semantic roles intact.
- Use Editorial New for display only when its licensed local font is available; otherwise use Georgia. Use Space Grotesk for body, metadata, and utility text. Display headings are editorial and restrained; body and labels remain plain and legible.
- Keep the exact spacing scale: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 96 px. The report itself uses a 12-column grid with a 16 px gutter; use that as the alignment reference, not a reason to redraw the approved composition.
- Use a 2 px rich-ink structural rule for the page/cover anchor. Use 1 px square outlines for cards and evidence frames; evidence-frame outlines and labels use `#16324F`. Do not introduce rounded card geometry. Recommendation-style emphasis, if it appears, uses a 4 px sapphire left rule rather than a new shape.
- Keep evidence frames square, with a white interior inside the pale evidence field. Evidence should read as evidence, not decoration.
- Do not go below the report's type floors: 10 pt body text and 8 pt running metadata in print. For the 1280 x 640 cover, choose on-screen sizes that remain clearly above those floors after export; do not solve space by shrinking labels into texture.
- Retain project attribution: `Punchlist · Independent experience review`. Do not add a personal byline or portfolio link. Keep the public posture clear: Punchlist v0.1 is production-ready within its declared capabilities.

## Platform accent boundary

For this Figma/social-cover handoff only, a platform accent may use an approved public logo alongside the primary accent, one supporting tone, evidence-frame treatment, and source label. The v0.1 generated report does not render platform logos. Neither surface may change the display/body type roles, grid, spacing scale, page anatomy, attribution, evidence hierarchy, severity language, or accessibility treatment. Do not imply affiliation, endorsement, or official platform authorship.

## Copy alignment

Match the README and synthetic report in plain terms. The social/cover should communicate: “Punchlist is a named-defect UX audit protocol for AI coding agents.” It can add “Task-led UX audit with named defects and evidence.” If space permits, use “v0.1 production-ready” as a status label.

Do not promise accuracy, coverage, time saved, quality scores, or outcomes. Do not use private, company-specific, customer, employer, or unapproved audit content. The synthetic report is an invented product and invented evidence, not a claim about a real organization.

## Paste-ready instruction

```text
Inspect this existing Figma frame first: [PASTE THE APPROVED FIGMA FRAME URL HERE]

This is a visual-alignment task for Punchlist’s public social/cover treatment. The project owner owns layout, scale, and composition. Preserve those decisions: do not replace or redraw the composition autonomously. Propose or perform only the requested visual alignment, then leave all other structure alone.

Reference repository assets: assets/social-preview.svg and assets/social-preview.png. Align with examples/synthetic/report.html and examples/synthetic/report.pdf, using themes/punchlist-default.json and templates/report/report.css as the source of truth.

Keep the frame 1280 x 640 with a clear internal safe area. Use #FFFFFF canvas; #10233D primary type and structural rules; #526273 secondary metadata; #2457D6 sapphire emphasis; #7353BA supporting tone; #F1F5F9 evidence background; and #16324F evidence labels/outlines. Use Editorial New for display only if its licensed local font is available, otherwise Georgia; use Space Grotesk for body and metadata. Keep the 4/8/12/16/20/24/32/40/48/64/96 px spacing scale. Use a 2 px #10233D structural rule and 1 px square evidence/card outlines (#16324F for evidence); no rounded evidence frames. Keep body and metadata visibly above the report’s 10 pt and 8 pt print floors after export.

For this Figma/social-cover task only, an approved public logo may accompany the primary accent, one supporting tone, evidence-frame treatment, and source label. Do not infer logo support in the v0.1 generated report; it renders platform name, accent, supporting tone, evidence treatment, and source reference only. Do not change typography roles, grid, spacing, page anatomy, project attribution, evidence hierarchy, severity language, or accessibility. Retain “Punchlist · Independent experience review” and do not add a personal byline or portfolio link. Keep “v0.1 production-ready” visible if a status label is used. Use only public, generic copy: “Punchlist is a named-defect UX audit protocol for AI coding agents.” “Task-led UX audit with named defects and evidence.” Do not add metrics, performance promises, affiliation claims, or any private/company audit content.

Afterward, return: (1) a screenshot of the updated frame and (2) measured evidence listing the frame size, text style names/sizes, hex colors, spacing and rule measurements, and every changed node ID. State whether you changed the frame or only proposed changes.
```
