# DC-SCOPE-02 — Selective Visit Scope

Status: **ADOPTED**

Date: 2026-09-18

## 1. Governing principle

The Master is a reference library, not a mandatory visit template.

Default behavior:
- freedom of selection;
- guidance when useful;
- constraint only when an explicit assignment or rule requires it.

This contract is subordinate only to the project's Quality First principle.

## 2. Visit creation

A new inspection:
1. selects institution and visit date;
2. pins the latest published Master Version;
3. starts with an empty SELECTIVE scope;
4. lets the inspector build the actual visit scope.

The system must not automatically materialize the complete Master for a new visit.

## 3. Scope granularity

The inspector can add:
- a complete reference branch;
- a single Specification;
- a single Checklist Item;
- local content absent from the Master.

Selecting a deep element creates only the structural ancestors required to preserve context.

Ancestors created only for that purpose use:

`scope_role = CONTEXT`

The intentionally selected node uses:

`scope_role = SELECTED`

## 4. Scope provenance

Every scoped snapshot records why it exists:

- LEGACY
- MANUAL
- GUIDE
- ASSIGNMENT
- LOCAL

A visit can contain several origins at the same time.

No visit-level FREE/GUIDED/LOCKED mode is required.

## 5. Scope state

Each scoped snapshot is either:
- ACTIVE
- EXCLUDED

Exclusion is soft.

It must not delete:
- the Snapshot;
- entered Specification values;
- Checklist status;
- observations;
- recommendations.

Restoration reactivates the same stored Snapshot.

## 6. Constraint semantics

Two independent concepts are required:

### scope_locked
The element cannot be removed from the visit scope.

### completion_required
The visit cannot be completed until the element is resolved.

These concepts must never be collapsed into one flag.

## 7. Local field reality

The inspector may create:
- a local root node;
- a local child node;
- a local specification;
- a local checklist item.

Local content:
- is usable immediately in the visit;
- uses `scope_origin = LOCAL`;
- creates a Proposal;
- does not modify the published Master directly.

The old redundant `local_addition` Boolean is replaced by scope origin.

## 8. Historical truth

Existing visits are migrated without rewriting their historical content.

Pre-selective visits are classified as:

`scope_mode = LEGACY_FULL`

Their existing non-local snapshots become LEGACY origin; their historical local additions become LOCAL origin.

New visits default to:

`scope_mode = SELECTIVE`

## 9. Progress

Progress is calculated from ACTIVE Checklist Item snapshots only.

EXCLUDED items do not affect the denominator.

NOT_APPLICABLE remains a resolved state for Progress.

## 10. Completion

Only ACTIVE entries participate in completion checks.

An ACTIVE Checklist Item with `completion_required = true` and status UNCHECKED blocks completion.

An ACTIVE Specification with `completion_required = true` and no meaningful value blocks completion.

## 11. Export

The canonical export becomes:

`inspection-export-v2`

It exports:
- pinned Master Version;
- visit scope mode;
- per-entry origin/state/role/lock metadata;
- completion requirement where applicable;
- Snapshot data;
- local Proposal trace when available.

EXCLUDED snapshots remain exportable because exclusion is a scope decision, not deletion.

## 12. Stage boundaries

### Stage A — Selective Scope Core
- selective creation;
- scope management;
- context ancestors;
- exclusion/restoration;
- local root content;
- progress/completion integration;
- migration;
- export v2.

### Stage B — Guides
Reusable optional recommendations built on stable logical IDs.

### Stage C — Assignments
Required scope and completion obligations supplied by an explicit assignment.

Guides and Assignments must build on this scope model rather than reintroducing full-Master materialization.

## 13. Core invariants

1. One pinned Master Version per visit.
2. New visit does not auto-copy the whole Master.
3. Snapshot text remains historically stable.
4. Single-element selection does not pull unrelated siblings.
5. CONTEXT is not equivalent to SELECTED.
6. Exclusion never destroys captured data.
7. Restore reuses the same Snapshot.
8. A Master source element is not duplicated within the same visit scope.
9. Local content remains local until Admin governance promotes it.
10. Published Master changes do not rewrite existing visits.
