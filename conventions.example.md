# Project conventions (example)

Copy to your project as `conventions.md`. Each entry records a **deliberate** design decision so audits stop re-flagging it. An entry needs an owner and a reason — "we like it" is a reason; absence of one is how accidents hide as conventions.

## Format

- **<what>** — <why it is deliberate>. (owner, date)

## Examples

- **Dark-only theme, no light mode** — product is a signal-viewing tool; verified domain convention. (the project owner, 2026-07-28)
- **Filter pills wrap; collection tabs scroll** — pills are compared as a set, tabs are navigation. (the project owner, 2026-07-29)
- **Half-step vertical padding (`py-2.5`) stays** — it determines the 40px data-row height matching the reference build. (the project owner, 2026-07-28)
