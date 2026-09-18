# CHANGELOG

## 2026-09-18 — Gate 6 JSON Export & Pilot Readiness

### Added
- Deterministic `inspection-export-v1` JSON export.
- Snapshot-based recursive export for Nodes, Specifications and Checklist Items.
- Local-addition and Proposal trace metadata.
- Owner/Admin export authorization.
- UTF-8 Arabic download.
- Fictitious local `seed_demo` command with safety guards.
- Local Pilot run instructions.
- SQLite/PostgreSQL backup/restore notes.
- Export schema documentation.
- Desktop/mobile/security human acceptance checklist.

### Verification
- Initial Gate 6 CI exposed a test-environment DEBUG mismatch in the positive seed test.
- Test corrected without weakening production guard.
- Final migration drift check: PASS.
- Django system check: PASS.
- Migrations: PASS.
- Automated tests: 54/54 PASS.
- Push CI: 35337239791.
- PR CI: 35337242562.

### Verdict
TECHNICAL-PASS. Human desktop/mobile acceptance is still required before PILOT-READY.

---

## 2026-09-18 — Gate 5 Local Additions / Governance / Version Publishing
- 46/46 tests PASS.
- PR #11 merged as `25f3cbd2d94ab96de35ebd4d2cfdcd2fd959f53b`.

## 2026-09-18 — Gate 4 Inspector Field Workflow
- 33/33 tests PASS.
- PR #9 merged as `b506095d4e5856b2016759962be94440c7536202`.

## 2026-09-18 — Gate 3 Admin Builder
- 23/23 tests PASS.
- PR #7 merged as `e55a81c18451ab42eb8da33a34ba98db4efd6e3b`.

## 2026-09-18 — Gate 2 Core Data & Authentication
- 13/13 tests PASS.
- PR #5 merged as `afc42baee093f7b0904fa8a1bc1355eb11e09bef`.

## 2026-09-18 — Gate 1 Technical Spike
- Django 5.2 LTS + PostgreSQL + Django Templates.
- PR #3 merged as `bac6caaf1b45ddc23f6a50155136ee5a63c66c0c`.

## 2026-09-18 — Foundation v0.1
- PR #1 merged as `9278700fcbf3113854e2bd0f553a5db051529d60`.
