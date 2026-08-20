# Security policy

## Report a vulnerability

Use [GitHub's private vulnerability reporting form](https://github.com/xenstalker02/punchlist/security/advisories/new) for a repository or workflow vulnerability. Do not open a public issue for a credential, private identifier, or confidential report output.

Include the affected version or commit, the affected file or workflow, the exposure path, and a minimal reproduction. Replace real secrets and customer data with synthetic values when they prove the same condition. Security fixes target the current `main` branch; v0.1 is the current maintained release line.

## Handle audit data separately

Ordinary audit data is not a vulnerability report. Classify it before inspection: public and logged-out by default, or `authorized-restricted` when explicit scope permits private material. Keep restricted evidence and reports with their authorized recipients, redact publication output, and get separate publication approval before sharing it.

Do not place credentials, local paths, private URLs, personal emails, customer identifiers, or unapproved screenshots in issues, pull requests, fixtures, or generated public reports. `.gitignore` is a convenience rule, not a confidentiality boundary. For a question about ordinary report handling or compatibility, use [SUPPORT.md](SUPPORT.md).
