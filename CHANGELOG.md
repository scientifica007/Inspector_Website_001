# CHANGELOG

## 2026-09-18 — Gate 2 Core Data & Authentication

### Added
- Reproducible initial Django migration committed to the repository.
- Automatic profile creation for new users.
- Admin / Inspector role baseline.
- Authenticated institution list and creation flow.
- Inspector-added institutions remain private to the creator until Admin review.
- Pending institution proposals for Admin moderation.
- Inspection draft creation.
- Automatic pinning to the latest published MasterVersion.
- Dynamic SpecificationValue snapshots.
- Server-side institution visibility rules.
- Arabic RTL/mobile institution and inspection forms.

### Verification
- Migration drift check: PASS.
- Django system check: PASS.
- Migration apply: PASS.
- Automated tests: 13/13 PASS.
- GitHub Actions run: 35332405047.

### Project control
- Gate 2 branch: `gate-2/core-data-auth`
- Gate 2 PR: #5
- Gate 2 issue: #4

### Next
Gate 3 — narrow Admin Builder for recursive structure, specifications and checklist items.

---

## 2026-09-18 — Gate 1 Technical Spike

### Validated
- Django 5.2 LTS as the recommended application framework.
- PostgreSQL as the Production database.
- Django Templates as the initial UI approach.
- Built-in authentication path and protected dashboard.
- Admin / Inspector role model.
- Recursive StructureNode.
- Dynamic SpecificationDefinition.
- MasterVersion and inspection pinning.
- Historical title snapshot behavior.
- Proposal model for field additions.
- Arabic RTL responsive shell.

### Verification
- GitHub Actions workflow: PASS.
- Dependency installation: PASS.
- `makemigrations`: PASS.
- `django check`: PASS.
- `migrate`: PASS.
- Automated tests: PASS.

### Scope Control
- HTMX remains optional and deferred.
- Full Admin Builder is not part of Gate 1.
- Full field workflow is not part of Gate 1.
- Production hosting is not locked yet.

### Project control
- Gate 1 branch: `spike/gate-1-django`
- Gate 1 PR: #3
- Gate 1 tracking issue: #2

---

## 2026-09-18 — Foundation v0.1

### Added
- Project charter.
- Recursive domain model.
- Dynamic specification model.
- Checklist status contract including NOT_APPLICABLE.
- Admin Builder concept.
- Inspector field workflow.
- Proposal moderation model.
- Draft / Publish / Version model.
- Historical snapshot rules.
- Delivery gates.
- Research notes from comparable systems.
- Decision log.
- CURRENT-STATE.json.

### Project control
- Foundation branch: `foundation/v0.1`
- PR #1: merged.
- Merge commit: `9278700fcbf3113854e2bd0f553a5db051529d60`
