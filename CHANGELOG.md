# CHANGELOG

## 2026-09-18 — Gate 4 Inspector Field Workflow

### Added
- Stable inspection snapshot materialization at visit creation.
- Snapshot metadata for dynamic specifications and item guidance.
- Recursive visit navigation.
- Dynamic input support for all V1 field types.
- Five-state checklist editing.
- Item observations.
- Node-level observations and recommendations.
- General observations and recommendations.
- Progress indicator.
- Explicit completion confirmation and completed-visit edit lock.
- Admin read-only viewing of inspectors' visits.
- RTL/mobile field workflow.

### Verification
- Migration drift check: PASS.
- Django system check: PASS.
- Migrations: PASS.
- Automated tests: 33/33 PASS.
- Push CI: 35335170791.
- PR CI: 35335189021.

### Project control
- Gate 4 branch: `gate-4/inspector-field-workflow`
- Gate 4 PR: #9
- Gate 4 issue: #8

### Next
Gate 5 — local additions, Proposal Inbox moderation, and version publish workflow.

---

## 2026-09-18 — Gate 3 Admin Builder
- 23/23 tests PASS.
- PR #7 merged as `e55a81c18451ab42eb8da33a34ba98db4efd6e3b`.

## 2026-09-18 — Gate 2 Core Data & Authentication
- 13/13 tests PASS.
- PR #5 merged as `afc42baee093f7b0904fa8a1bc1355eb11e09bef`.

## 2026-09-18 — Gate 1 Technical Spike
- Django 5.2 LTS + PostgreSQL + Django Templates selected.
- PR #3 merged as `bac6caaf1b45ddc23f6a50155136ee5a63c66c0c`.

## 2026-09-18 — Foundation v0.1
- Project charter, domain model, architecture, workflows, delivery gates and decision log.
- PR #1 merged as `9278700fcbf3113854e2bd0f553a5db051529d60`.
