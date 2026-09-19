# DC-SCOPE-02 — Selective Visit Scope

Status: **ADOPTED — amended through A-C3**

Date: 2026-09-18
Current amendment: 2026-09-19

## 1. Governing principle

The inspection reference library is a source of reusable professional content, not a mandatory visit template.

Default behavior:
- freedom of selection;
- guidance when useful;
- constraint only when an explicit assignment or rule requires it.

No visit-level FREE/GUIDED/LOCKED mode is required. A single visit may combine MANUAL, GUIDE, ASSIGNMENT and LOCAL content.

## 2. Reference library

References are independent entities.

- SHARED references are available to inspectors.
- PRIVATE references belong to one inspector.
- Creating or editing one reference does not supersede another.
- Admin may create, edit and hard-delete shared reference content.
- Inspectors may create and edit their own private references.
- A private reference is generalized only through an explicit ReferenceSubmission.

The old one-current-published-Master + Draft + Publish product model is retired.

## 3. Visit creation and frozen source

A new inspection:
1. selects institution and visit date;
2. optionally selects an available reference;
3. if a reference is selected, creates an internal per-visit SNAPSHOT copy;
4. starts with an empty SELECTIVE scope;
5. lets the inspector build the actual visit scope from the frozen copy or local content.

The original source reference is not a live dependency after creation. Later source edits or deletion do not rewrite the draft.

## 4. Scope granularity

The inspector can add:
- a complete frozen-reference branch;
- a single description;
- a single checklist item;
- local content absent from the reference.

Selecting a deep element creates only the structural ancestors required to preserve context.
Ancestors created only for that purpose use scope_role = CONTEXT; the intentionally selected node uses scope_role = SELECTED.

## 5. Scope provenance

Every scoped snapshot records why it exists: LEGACY / MANUAL / GUIDE / ASSIGNMENT / LOCAL.
Several origins may coexist in the same visit.

## 6. Scope state

Each scoped snapshot is either ACTIVE or EXCLUDED.
Exclusion is soft and must not delete the Snapshot, entered description values, checklist status, observations or recommendations.
Restoration reactivates the same stored Snapshot.

## 7. Constraint semantics

scope_locked means the element cannot be removed from the visit scope.
completion_required means the visit cannot be completed until the element is resolved.
These concepts must never be collapsed into one flag.

## 8. Local field reality

The inspector may create a local root node, local child node, local description or local checklist item.
Local content is usable immediately, uses scope_origin = LOCAL, remains private to the visit, creates no automatic Admin Proposal, and modifies no reference.
If reusable content is desired, the reusable unit is a PRIVATE reference and generalization is requested explicitly through ReferenceSubmission.

## 9. Historical truth and lifecycle

Existing visits are migrated without rewriting captured values/results.
Pre-selective visits are LEGACY_FULL; new visits default to SELECTIVE.
A DRAFT may be deleted by its owner. A COMPLETED inspection is a preserved professional record and cannot be edited or deleted.

## 10. Progress and completion

Progress is calculated from ACTIVE checklist-item snapshots only.
EXCLUDED items do not affect the denominator. NOT_APPLICABLE remains resolved for Progress.
Only ACTIVE entries participate in completion checks.
An ACTIVE checklist item with completion_required=true and status UNCHECKED blocks completion.
An ACTIVE description with completion_required=true and no meaningful value blocks completion.

## 11. Export

The canonical export is inspection-export-v3.
It exports source reference identity when still available plus the stored source name, visit scope metadata, Snapshot data, and historical Proposal trace only where old data already contains it.
The internal per-visit reference SNAPSHOT is an implementation detail and is not exported as the business reference identity.

## 12. Stage boundaries

### Stage A — Selective Scope Core + Correction Gate
- selective creation;
- frozen visit source;
- scope management;
- context ancestors;
- exclusion/restoration;
- local authoring;
- independent reference library;
- private references and explicit ReferenceSubmission;
- draft deletion / completed-record protection;
- progress/completion integration;
- migrations;
- export v3.

### Stage B — Guides
Reusable optional recommendations built on stable logical IDs. Applying a Guide may add suggested scope with origin=GUIDE, but must remain optional and removable.

### Stage C — Assignments
Required scope and completion obligations supplied by an explicit assignment. Assignments may use scope_locked and/or completion_required as distinct controls.

Guides and Assignments must build on this scope model rather than reintroducing full-reference materialization.

## 13. Core invariants

1. No global current reference supersedes all others.
2. A visit may start from a chosen reference or without one.
3. A chosen reference is frozen into an internal per-visit copy at creation.
4. New visits do not auto-materialize the complete reference into ACTIVE scope.
5. Snapshot text remains historically stable.
6. Single-element selection does not pull unrelated siblings.
7. CONTEXT is not equivalent to SELECTED.
8. Exclusion never destroys captured data.
9. Restore reuses the same stored Snapshot.
10. A frozen source element is not duplicated within the same visit scope.
11. Local visit content stays local unless the inspector deliberately uses the private-reference workflow.
12. Editing or deleting an original reference does not rewrite an existing visit.
13. COMPLETED inspection data is immutable and non-deletable.


## 14. B-GUIDE-01 implementation contract

Status: **ADOPTED**

- Guides are optional reusable scope recommendations.
- A Guide belongs to one SHARED reference.
- Guide targets use stable logical IDs.
- Applying a Guide is explicit and idempotent.
- Newly added content uses GUIDE origin.
- Existing content keeps its previous origin.
- Guide application never enables scope_locked or completion_required.
- Matching is performed against the frozen per-visit reference.
- Missing targets are skipped and counted; the frozen source is never refreshed implicitly.
- GuideApplication preserves application-time Guide metadata.
- Required/locked semantics remain exclusively in Stage C Assignments.


## 15. C-ASSIGN-01 implementation contract

Status: **ADOPTED**

- Assignment is a formal obligation bound to one existing DRAFT inspection.
- No LOCKED visit mode is introduced.
- Admin drafts the assignment before issue; draft assignments are invisible to the inspector.
- Targets resolve against the inspection's frozen reference by Stable ID.
- Each entry requires scope_locked and/or completion_required.
- Issue is atomic after full preflight.
- New scope receives ASSIGNMENT origin; existing scope retains existing provenance.
- Branch locking applies to branch structure and contained descriptions/items.
- Branch completion requirements apply to descriptions/items, not to node notes.
- AssignmentEffect records obligation provenance.
- Effective constraints preserve baseline historical constraints and all still-issued overlapping assignments.
- Revocation requires a reason, is DRAFT-only, preserves visit data and recomputes effective constraints.
- COMPLETED visits are immutable: no issue or revocation.
- Export audit contract advances to inspection-export-v4.
