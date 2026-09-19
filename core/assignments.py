from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    Assignment,
    AssignmentEffect,
    AssignmentEntry,
    AssignmentEntryType,
    AssignmentStatus,
    ChecklistItem,
    InspectionItemResult,
    InspectionNode,
    InspectionStatus,
    ScopeOrigin,
    ScopeState,
    SpecificationDefinition,
    SpecificationValue,
    StructureNode,
)
from .services import (
    add_scope_branch,
    add_scope_item,
    add_scope_specification,
)


def _active_path(node):
    current = node
    reference_id = node.master_version_id
    while current is not None:
        if current.master_version_id != reference_id or not current.active:
            return False
        current = current.parent
    return True


def _resolve_entry(assignment, entry):
    inspection = assignment.inspection
    frozen_reference_id = inspection.master_version_id
    if not frozen_reference_id:
        raise ValidationError("الزيارة لا تحتوي مرجعًا مجمدًا يمكن إصدار التكليف عليه.")

    if entry.entry_type == AssignmentEntryType.BRANCH:
        target = (
            StructureNode.objects.filter(
                master_version_id=frozen_reference_id,
                stable_id=entry.stable_id,
                active=True,
            )
            .select_related("parent")
            .first()
        )
        if target is None or not _active_path(target):
            raise ValidationError(
                f"تعذر العثور على الفرع «{entry.label_snapshot}» داخل لقطة الزيارة."
            )
        return target

    if entry.entry_type == AssignmentEntryType.SPECIFICATION:
        target = (
            SpecificationDefinition.objects.filter(
                node__master_version_id=frozen_reference_id,
                stable_id=entry.stable_id,
                active=True,
            )
            .select_related("node")
            .first()
        )
        if target is None or not _active_path(target.node):
            raise ValidationError(
                f"تعذر العثور على الوصف «{entry.label_snapshot}» داخل لقطة الزيارة."
            )
        return target

    if entry.entry_type == AssignmentEntryType.ITEM:
        target = (
            ChecklistItem.objects.filter(
                node__master_version_id=frozen_reference_id,
                stable_id=entry.stable_id,
                active=True,
            )
            .select_related("node")
            .first()
        )
        if target is None or not _active_path(target.node):
            raise ValidationError(
                f"تعذر العثور على البند «{entry.label_snapshot}» داخل لقطة الزيارة."
            )
        return target

    raise ValidationError("نوع عنصر التكليف غير معروف.")


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
        InspectionNode.objects.filter(pk=pk, inspection=inspection).exclude(
            scope_origin=origin
        ).update(scope_origin=origin)

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


def _active_source_subtree(root):
    nodes = []

    def walk(node):
        if not node.active:
            return
        nodes.append(node)
        for child in node.children.filter(active=True).order_by("sort_order", "id"):
            walk(child)

    walk(root)
    return nodes


def _effect_for_node(entry, node):
    if not entry.scope_locked:
        return None
    effect, _ = AssignmentEffect.objects.get_or_create(
        assignment_entry=entry,
        node=node,
        defaults={
            "scope_locked": True,
            "completion_required": False,
        },
    )
    return effect


def _effect_for_specification(entry, value):
    effect, _ = AssignmentEffect.objects.get_or_create(
        assignment_entry=entry,
        specification=value,
        defaults={
            "scope_locked": entry.scope_locked,
            "completion_required": entry.completion_required,
        },
    )
    return effect


def _effect_for_item(entry, result):
    effect, _ = AssignmentEffect.objects.get_or_create(
        assignment_entry=entry,
        item=result,
        defaults={
            "scope_locked": entry.scope_locked,
            "completion_required": entry.completion_required,
        },
    )
    return effect


def _apply_branch_entry(assignment, entry, source):
    inspection = assignment.inspection
    add_scope_branch(
        inspection,
        source,
        origin=ScopeOrigin.ASSIGNMENT,
        locked=False,
        completion_required=False,
    )

    effects = []
    for source_node in _active_source_subtree(source):
        snapshot = inspection.inspection_nodes.get(source_node=source_node)
        node_effect = _effect_for_node(entry, snapshot)
        if node_effect:
            effects.append(node_effect)

        for spec in source_node.specifications.filter(active=True).order_by(
            "sort_order", "id"
        ):
            value = snapshot.specification_values.get(source_specification=spec)
            effects.append(_effect_for_specification(entry, value))

        for item in source_node.items.filter(active=True).order_by("sort_order", "id"):
            result = snapshot.item_results.get(source_item=item)
            effects.append(_effect_for_item(entry, result))

    return effects


def _apply_specification_entry(assignment, entry, source):
    value = add_scope_specification(
        assignment.inspection,
        source,
        origin=ScopeOrigin.ASSIGNMENT,
        locked=False,
        completion_required=False,
    )
    return [_effect_for_specification(entry, value)]


def _apply_item_entry(assignment, entry, source):
    result = add_scope_item(
        assignment.inspection,
        source,
        origin=ScopeOrigin.ASSIGNMENT,
        locked=False,
        completion_required=False,
    )
    return [_effect_for_item(entry, result)]


def _apply_entry(assignment, entry, source):
    if entry.entry_type == AssignmentEntryType.BRANCH:
        return _apply_branch_entry(assignment, entry, source)
    if entry.entry_type == AssignmentEntryType.SPECIFICATION:
        return _apply_specification_entry(assignment, entry, source)
    if entry.entry_type == AssignmentEntryType.ITEM:
        return _apply_item_entry(assignment, entry, source)
    raise ValidationError("نوع عنصر التكليف غير معروف.")


def _active_assignment_effects_for_node(node):
    return AssignmentEffect.objects.filter(
        node=node,
        assignment_entry__assignment__status=AssignmentStatus.ISSUED,
    )


def _active_assignment_effects_for_specification(value):
    return AssignmentEffect.objects.filter(
        specification=value,
        assignment_entry__assignment__status=AssignmentStatus.ISSUED,
    )


def _active_assignment_effects_for_item(result):
    return AssignmentEffect.objects.filter(
        item=result,
        assignment_entry__assignment__status=AssignmentStatus.ISSUED,
    )


def recompute_node_constraints(node):
    locked = node.base_scope_locked or _active_assignment_effects_for_node(
        node
    ).filter(scope_locked=True).exists()
    if node.scope_locked != locked:
        node.scope_locked = locked
        node.save(update_fields=["scope_locked"])


def recompute_specification_constraints(value):
    effects = _active_assignment_effects_for_specification(value)
    locked = value.base_scope_locked or effects.filter(scope_locked=True).exists()
    required = value.base_completion_required or effects.filter(
        completion_required=True
    ).exists()
    updates = []
    if value.scope_locked != locked:
        value.scope_locked = locked
        updates.append("scope_locked")
    if value.completion_required != required:
        value.completion_required = required
        updates.append("completion_required")
    if updates:
        value.save(update_fields=updates)


def recompute_item_constraints(result):
    effects = _active_assignment_effects_for_item(result)
    locked = result.base_scope_locked or effects.filter(scope_locked=True).exists()
    required = result.base_completion_required or effects.filter(
        completion_required=True
    ).exists()
    updates = []
    if result.scope_locked != locked:
        result.scope_locked = locked
        updates.append("scope_locked")
    if result.completion_required != required:
        result.completion_required = required
        updates.append("completion_required")
    if updates:
        result.save(update_fields=updates)


def _recompute_effect_targets(effects):
    node_ids = {
        effect.node_id for effect in effects if effect.node_id is not None
    }
    specification_ids = {
        effect.specification_id
        for effect in effects
        if effect.specification_id is not None
    }
    item_ids = {
        effect.item_id for effect in effects if effect.item_id is not None
    }

    for node in InspectionNode.objects.filter(pk__in=node_ids):
        recompute_node_constraints(node)
    for value in SpecificationValue.objects.filter(pk__in=specification_ids):
        recompute_specification_constraints(value)
    for result in InspectionItemResult.objects.filter(pk__in=item_ids):
        recompute_item_constraints(result)


@transaction.atomic
def issue_assignment(assignment, user):
    assignment = (
        Assignment.objects.select_for_update()
        .select_related("inspection")
        .get(pk=assignment.pk)
    )
    inspection = assignment.inspection

    if assignment.status != AssignmentStatus.DRAFT:
        raise ValidationError("لا يمكن إصدار تكليف سبق إصداره أو إلغاؤه.")
    if inspection.status != InspectionStatus.DRAFT:
        raise ValidationError("لا يمكن إصدار تكليف لزيارة مكتملة.")

    entries = list(assignment.entries.all().order_by("sort_order", "id"))
    if not entries:
        raise ValidationError("أضف عنصر تكليف واحدًا على الأقل قبل الإصدار.")

    resolved = []
    for entry in entries:
        if not entry.scope_locked and not entry.completion_required:
            raise ValidationError(
                f"عنصر التكليف «{entry.label_snapshot}» لا يحمل أي التزام."
            )
        resolved.append((entry, _resolve_entry(assignment, entry)))

    origins = _capture_existing_origins(inspection)
    effects = []
    for entry, source in resolved:
        effects.extend(_apply_entry(assignment, entry, source))

    _restore_existing_origins(inspection, origins)

    assignment.status = AssignmentStatus.ISSUED
    assignment.issued_by = user
    assignment.issued_at = timezone.now()
    assignment.save(
        update_fields=["status", "issued_by", "issued_at", "updated_at"]
    )

    _recompute_effect_targets(effects)
    return assignment


@transaction.atomic
def revoke_assignment(assignment, user, reason):
    assignment = (
        Assignment.objects.select_for_update()
        .select_related("inspection")
        .get(pk=assignment.pk)
    )
    inspection = assignment.inspection
    reason = (reason or "").strip()

    if assignment.status != AssignmentStatus.ISSUED:
        raise ValidationError("يمكن إلغاء التكليف الصادر فقط.")
    if inspection.status != InspectionStatus.DRAFT:
        raise ValidationError("لا يمكن إلغاء تكليف بعد تثبيت الزيارة.")
    if not reason:
        raise ValidationError("سبب إلغاء التكليف إلزامي.")

    effects = list(
        AssignmentEffect.objects.filter(
            assignment_entry__assignment=assignment
        ).select_related(
            "node",
            "specification",
            "item",
        )
    )

    assignment.status = AssignmentStatus.REVOKED
    assignment.revoked_by = user
    assignment.revoked_at = timezone.now()
    assignment.revocation_reason = reason
    assignment.save(
        update_fields=[
            "status",
            "revoked_by",
            "revoked_at",
            "revocation_reason",
            "updated_at",
        ]
    )

    _recompute_effect_targets(effects)
    return assignment
