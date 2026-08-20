# Releasing Punchlist

This checklist prepares a reviewed change for release. Review the public boundary in the [README](README.md) before running it.

1. Confirm the working tree contains only intended release files and that the changelog names the exact approved version and date.
2. Scan public files, generated output, examples, issues copied into notes, and release text for private organization names, credentials, local paths, private URLs, personal emails, customer identifiers, and unapproved screenshots.
3. Regenerate the committed synthetic HTML and PDF from the synthetic audit and projection. Confirm they contain invented data only.
4. Inspect the synthetic HTML at ordinary reading size and its PDF print output for overflow, clipping, unresolved placeholders, missing evidence, and broken links.
5. Run `python scripts/validate.py`, `python -m unittest discover -s tests -v`, and `npm run test:report` from a clean install with Playwright Chromium available.
6. Check README, governance, synthetic HTML, synthetic PDF, and changelog links in a fresh clone or clean worktree.
7. Create the exact annotated release tag only after the release contents and version are approved.
## Publish authorization

<!-- governance: fresh-separate-publish-authorization -->

Request fresh, separate authorization to publish the approved tag, release notes, and any artifacts. Do not push, publish, or create a release without it.
