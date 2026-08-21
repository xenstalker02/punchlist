# Changelog

All notable changes to Punchlist will be recorded here.

## Unreleased

### Fixed

- Preserved verified-fixed findings in the traceable ledger, counts, projection, and rendered report with their resweep evidence.
- Allowed authorized-restricted audits to validate before publication while retaining explicit recipient, redaction, evidence, and publication gates for generated reports.
- Enforced the schema constraints used by the report contracts, including array limits, dynamic object values, cross-runtime-safe theme patterns, and a shared finding severity basis.
- Made the PDF command fail safely when its browser dependency is unavailable, without exposing a checkout path.

### Changed

- Expanded privacy validation to public source, style, text, and extensionless files, with reviewed fixture-only exclusions and line-level locations.
- Generated tagged PDFs and exposed their accessibility state through the PDF inspector.
- Pinned the supported Node and npm toolchain in package metadata and CI, and added Python dependency updates to Dependabot.

## 0.1.0 - 2026-08-20

First production-ready release of the traceable Punchlist audit-to-report system.

### Added

- A synthetic audit-to-projection-to-render example, with self-contained HTML and a PDF export from the verified HTML.
- Recipient-safe report contracts, privacy checks, and report visual verification.
- Public governance for conduct, support, security, contribution, and release review.
- A standard-library validator for taxonomy schemas, category counts, evidence requirements, example findings, and internal file references.
- GitHub Actions validation on pushes and pull requests.
- Schema-valid synthetic fixtures for report validation.
- Contribution, security, agent, issue, and pull-request guidance.
- Social-preview source and export.
- An experience-review template for audience-facing task and journey reports.

### Changed

- Made the task-led `experience` profile the default while retaining an explicit `implementation` profile for technical QA.
- Reframed the README and social preview around the user journey, symptom, named defect, and evidence model.
- Replaced incident-derived evaluation narratives with generic capability checks and explicitly non-evidentiary taxonomy illustrations.
