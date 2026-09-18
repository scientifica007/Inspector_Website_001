# GATE 2 RESULT — Core Data & Authentication

## Verdict
**PASS**

## Implemented

### Accounts and roles
- Django authentication/session flow remains the central authentication mechanism.
- New users receive a Profile automatically.
- Superusers are initialized as Admin; ordinary users as Inspector.

### Institutions
- Authenticated users can list available institutions.
- Admin-created institutions are immediately verified.
- Inspector-created institutions are immediately usable by their creator but remain PENDING.
- Pending institutions are not visible to other inspectors.
- Inspector additions create a Proposal for future Admin moderation.
- Duplicate institution names are rejected case-insensitively at the form layer.

### Inspection drafts
- Inspector can create a visit draft.
- Inspector identity is assigned server-side and is not selectable by the client.
- The visit is pinned automatically to the latest PUBLISHED MasterVersion.
- Creation is blocked when no published MasterVersion exists.

### Data model
- Initial migration is committed and reproducible.
- SpecificationValue is part of the core schema.
- Structure/Specification/Inspection snapshots preserve historical wording.

## Automated evidence

CI run: `35332405047`

- committed migration drift check: PASS
- `python manage.py check`: PASS
- migrations: PASS
- tests: **13/13 PASS**

Covered cases include:
- login protection;
- inspector data isolation;
- Admin visibility;
- automatic role profiles;
- pending institution proposals;
- pending institution visibility isolation;
- duplicate-name validation;
- latest published MasterVersion pinning;
- missing MasterVersion handling;
- recursive nodes;
- dynamic specification snapshots;
- NOT_APPLICABLE status contract.

## Deferred intentionally

- Admin Builder UX;
- proposal approval UI;
- publish/version editing UX;
- checklist field renderer;
- autosave;
- export;
- hosting.

These remain outside Gate 2.
