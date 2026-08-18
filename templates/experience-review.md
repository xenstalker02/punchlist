# Experience review template

Use this view for a hiring manager, product team, or stakeholder who needs the product judgment before the implementation detail. It is a presentation layer over canonical Punchlist findings, not a replacement for them.

## 1. Cover

- A plain-language statement of the task friction, not the product name plus “audit.”
- One-sentence task: user, goal, entry point, state, and device.
- Method and limit: heuristic review, not user research.

## 2. Journey

- Show the smallest complete path as 3–5 moments.
- Mark where confidence or task progress changed.
- Include a short “what held up” section from the orientation pass.

## 3. Lead findings

Use one page or section per decision-relevant finding:

1. **Human headline** — describe what became difficult.
2. **Journey moment** — where it happened.
3. **User symptom** — what the person had to infer, remember, repeat, or recover from.
4. **Punchlist name and standard** — keep the taxonomy visible without making it the headline.
5. **Evidence** — screenshot, interaction result, rendered measurement, or content read.
6. **Recommendation** — the smallest product change that addresses the symptom.

If the condition is real but no definition fits, write **Taxonomy gap** and keep it out of the defect count. Never rename the nearest defect to make the story cleaner.

## 4. What works

Show the strongest moment in the same journey and explain which signals restore progress or trust. This is context, not a score or a trade against confirmed defects.

## 5. Opportunities and next test

- Group recommendations by the user decision they support, not by DOM element or taxonomy category.
- State the next test with the people whose behavior could overturn the recommendation.
- Name untested states and devices.

## 6. Technical appendix

Put standards and implementation findings here when they are valid but do not materially shape the declared task. Preserve defect id, surface, symptom, evidence, severity, and fix so the work remains actionable.
