# CHANGELOG

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

### Next
Gate 2 — production migrations, base roles/authorization, institutions and inspection draft foundation.

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
