# CHANGELOG

## Unreleased — DC-SCOPE-02 Stage A: Selective Visit Scope Core

### A-C1 — Workspace Separation & Navigation
- Replaced the visit-list landing screen with a role-aware home workspace; visits now have a dedicated list route.
- Split draft work into explicit preparation and field-execution workspaces without adding a visit mode.
- Added hierarchical breadcrumbs and child navigation for visit nodes.
- Inspector-facing “specification” terminology is now “description” (وصف/أوصاف) while internal model names remain unchanged.
- Local authoring actions are presented as explicit buttons in preparation screens.
- Added field-state color affordances while preserving textual status labels.
- Added bottom spacing to local-addition forms.

### A-C2 — Local Authoring Operations
- Draft owners can edit LOCAL branches, descriptions and checklist items during preparation.
- Reference snapshots remain immutable; inspectors can copy them as independent LOCAL content.
- Added duplicate-here, copy-to and move-to operations; branch copies recursively clone the active prepared subtree.
- Copies carry design only: description values are empty and checklist results restart as UNCHECKED with empty observations.
- Local removal is soft; removed content is listed separately and can be restored.
- Pending proposals are updated in place on edit/move, withdrawn on removal, and re-proposed on restore.
- Editing content after an already-resolved proposal creates a new PENDING proposal without rewriting the historical decision.
- Added Proposal status WITHDRAWN and migration 0005.

### A-C3.1 — Independent Reference Library Core
- Replaced the single-current-reference UX with a library of independent inspection references.
- Added human reference names, SHARED/PRIVATE visibility and optional ownership metadata.
- Admin can create multiple shared references without superseding earlier ones.
- Admin can hard-delete references, nodes, descriptions and checklist items; visit snapshots remain intact.
- New visits explicitly choose an available reference or start blank.
- Inspection source reference is now nullable and stores a reference-name snapshot so source deletion does not delete the visit.
- JSON export advances to `inspection-export-v3` and reports `reference` metadata instead of a version number.
- Added migration `0006_reference_library_core` with legacy classification and visit-name snapshot backfill.
- Legacy `number/status/published_at` fields remain temporarily as non-authoritative migration metadata and no longer drive builder or visit creation behavior.

### A-C3.2 — Private References & Explicit Generalization
- Inspectors can create and edit private references that are visible only to their owner.
- Any visible reference can be cloned into an independent private reference.
- Visit-local authoring no longer creates Proposal records automatically.
- A private reference is submitted to Admin only through an explicit “اقتراح للتعميم” action.
- Submission stores a frozen JSON snapshot, so later private edits or deletion do not change the Admin review payload.
- Rejection leaves the private reference unchanged; approval creates a new independent SHARED reference.
- Added `ReferenceSubmission`, explicit PENDING/APPROVED/REJECTED/WITHDRAWN states, and migration `0007_private_reference_submission`.
- Added `InspectionNode.inspectable_snapshot` so visit-local semantics no longer depend on legacy Proposal payloads.
- Legacy NODE/DESCRIPTION/ITEM Proposal records remain stored for history but are hidden from the active Admin inbox and cannot be approved through the A-C3 flow.

### Changed
- New visits start with an empty selective scope and may choose an available reference explicitly.
- The Master is treated as a reference library rather than a mandatory full-visit template.
- Inspectors can add a full branch, a single specification, or a single checklist item.
- Structural ancestors are materialized as CONTEXT only when needed.
- Scope exclusion is soft and preserves captured data for later restoration.
- Progress counts ACTIVE checklist items only.
- Completion can enforce independent `completion_required` obligations.
- Local content now uses `scope_origin=LOCAL` instead of a redundant `local_addition` flag.
- Local root nodes are supported and continue through Proposal governance.
- Canonical JSON export becomes `inspection-export-v2` with explicit scope metadata.

### Data migration
- Added `0004_selective_visit_scope`.
- Existing visits are classified as `LEGACY_FULL`.
- Existing non-local snapshots become `LEGACY`; historical local additions become `LOCAL`.
- Existing values, results, observations and Proposal links are retained.
- Migration has an explicit reverse mapping for the former local-addition flag.

### Verification
- Migration drift check, Django system check and migration application are part of CI.
- Dedicated selective-scope invariants and legacy-data migration tests added.
- Human browser/mobile acceptance remains required before merge/PILOT-READY.

---

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
- Final push CI: 35337419494.
- Final PR CI: 35337422182.

### Project control
- PR #13 merged as `c752d61a9431eb5f7594c61447182a71acef69b2`.
- Frozen human-test candidate: `pilot/v0.1-rc1` at the same commit.

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
