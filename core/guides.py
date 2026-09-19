from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    ChecklistItem,
    Guide,
    GuideApplication,
    GuideEntryType,
    InspectionItemResult,
    InspectionNode,
    InspectionStatus,
    ScopeOrigin,
    SpecificationDefinition,
    SpecificationValue,
    StructureNode,
)
from .services import (
    add_scope_branch,
    add_scope_item,
    add_scope_specification,
)


def guide_snapshot(guide):
    return {
        "name": guide.name,
        "description": guide.description,
        "reference_id": guide.reference_id,
        "entries": [
            {
                "entry_type": entry.entry_type,
                "stable_id": str(entry.stable_id),
                "label": entry.label_snapshot,
                "sort_order": entry.sort_order,
            }
            for entry in guide.entries.all().order_by("sort_order", "id")
        ],
    }


def compatible_guides(inspection):
    if not inspection.source_reference_id:
        return Guide.objects.none()
    return Guide.objects.filter(reference_id=inspection.source_reference_id).order_by(
        "name", "id"
    )


def _capture_existing_origins(inspection):
    return {
        "nodes": dict(
            inspection.inspection_nodes.values_list("id", "scope_origin")
        ),
        "specifications": dict(
            SpecificationValue.objects.filter(
                inspection_node__inspection=inspection
            ).values_list("id", "scope_origin")
        ),
        "items": dict(
            InspectionItemResult.objects.filter(
                inspection_node__inspection=inspection
            ).values_list("id", "scope_origin")
        ),
    }


def _restore_existing_origins(inspection, origins):
    for pk, origin in origins["nodes"].items():
        InspectionNode.objects.filter(
            pk=pk,
            inspection=inspection,
        ).exclude(scope_origin=origin).update(scope_origin=origin)

    for pk, origin in origins["specifications"].items():
        SpecificationValue.objects.filter(
            pk=pk,
            inspection_node__inspection=inspection,
        ).exclude(scope_origin=origin).update(scope_origin=origin)

    for pk, origin in origins["items"].items():
        InspectionItemResult.objects.filter(
            pk=pk,
            inspection_node__inspection=inspection,
        ).exclude(scope_origin=origin).update(scope_origin=origin)


def _resolve_entry(inspection, entry):
    frozen_reference_id = inspection.master_version_id
    if not frozen_reference_id:
        return None

    if entry.entry_type == GuideEntryType.BRANCH:
        return (
            StructureNode.objects.filter(
                master_version_id=frozen_reference_id,
                stable_id=entry.stable_id,
                active=True,
            )
            .select_related("parent")
            .first()
        )

    if entry.entry_type == GuideEntryType.SPECIFICATION:
        return (
            SpecificationDefinition.objects.filter(
                node__master_version_id=frozen_reference_id,
                stable_id=entry.stable_id,
                active=True,
            )
            .select_related("node")
            .first()
        )

    if entry.entry_type == GuideEntryType.ITEM:
        return (
            ChecklistItem.objects.filter(
                node__master_version_id=frozen_reference_id,
                stable_id=entry.stable_id,
                active=True,
            )
            .select_related("node")
            .first()
        )

    return None


def _exact_target_exists(inspection, entry, target):
    if target is None:
        return False
    if entry.entry_type == GuideEntryType.BRANCH:
        return inspection.inspection_nodes.filter(source_node=target).exists()
    if entry.entry_type == GuideEntryType.SPECIFICATION:
        return SpecificationValue.objects.filter(
            inspection_node__inspection=inspection,
            source_specification=target,
        ).exists()
    if entry.entry_type == GuideEntryType.ITEM:
        return InspectionItemResult.objects.filter(
            inspection_node__inspection=inspection,
            source_item=target,
        ).exists()
    return False


def _apply_entry(inspection, entry, target):
    if entry.entry_type == GuideEntryType.BRANCH:
        add_scope_branch(
            inspection,
            target,
            origin=ScopeOrigin.GUIDE,
            locked=False,
            completion_required=False,
        )
        return

    if entry.entry_type == GuideEntryType.SPECIFICATION:
        add_scope_specification(
            inspection,
            target,
            origin=ScopeOrigin.GUIDE,
            locked=False,
            completion_required=False,
        )
        return

    if entry.entry_type == GuideEntryType.ITEM:
        add_scope_item(
            inspection,
            target,
            origin=ScopeOrigin.GUIDE,
            locked=False,
            completion_required=False,
        )
        return

    raise ValidationError("نوع عنصر الدليل غير معروف.")


@transaction.atomic
def apply_guide(inspection, guide, user):
    inspection = inspection.__class__.objects.select_for_update().get(pk=inspection.pk)
    guide = Guide.objects.select_for_update().get(pk=guide.pk)

    if inspection.status != InspectionStatus.DRAFT:
        raise ValidationError("لا يمكن تطبيق دليل على زيارة مكتملة.")
    if not inspection.master_version_id:
        raise ValidationError("هذه الزيارة لا تحتوي لقطة مرجع يمكن تطبيق الدليل عليها.")
    if inspection.source_reference_id != guide.reference_id:
        raise ValidationError("هذا الدليل لا ينتمي إلى مرجع مصدر هذه الزيارة.")

    existing_application = GuideApplication.objects.filter(
        inspection=inspection,
        guide=guide,
    ).first()
    if existing_application:
        return existing_application, False

    origins = _capture_existing_origins(inspection)
    details = []
    applied_count = 0
    skipped_count = 0

    for entry in guide.entries.all().order_by("sort_order", "id"):
        target = _resolve_entry(inspection, entry)
        if target is None:
            skipped_count += 1
            details.append(
                {
                    "entry_type": entry.entry_type,
                    "stable_id": str(entry.stable_id),
                    "label": entry.label_snapshot,
                    "status": "missing",
                }
            )
            continue

        existed_before = _exact_target_exists(inspection, entry, target)
        try:
            _apply_entry(inspection, entry, target)
        except ValidationError as exc:
            skipped_count += 1
            details.append(
                {
                    "entry_type": entry.entry_type,
                    "stable_id": str(entry.stable_id),
                    "label": entry.label_snapshot,
                    "status": "unavailable",
                    "reason": " ".join(exc.messages),
                }
            )
            continue

        applied_count += 1
        details.append(
            {
                "entry_type": entry.entry_type,
                "stable_id": str(entry.stable_id),
                "label": entry.label_snapshot,
                "status": "already_present" if existed_before else "applied",
            }
        )

    # GUIDE must never rewrite provenance of an existing visit snapshot.
    _restore_existing_origins(inspection, origins)

    application = GuideApplication.objects.create(
        inspection=inspection,
        guide=guide,
        guide_name_snapshot=guide.name,
        guide_snapshot=guide_snapshot(guide),
        applied_by=user,
        applied_count=applied_count,
        skipped_count=skipped_count,
        result_details=details,
    )
    return application, True
