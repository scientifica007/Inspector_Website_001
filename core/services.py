from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db import models
from django.db.models import Max

from .models import (
    ChecklistItem,
    InspectionItemResult,
    InspectionNode,
    InspectionScopeMode,
    MasterStatus,
    MasterVersion,
    ReferenceVisibility,
    Role,
    ScopeOrigin,
    ScopeRole,
    ScopeState,
    SpecificationDefinition,
    SpecificationValue,
    StructureNode,
)

def visible_references(user):
    references = MasterVersion.objects.all()
    if user.is_superuser or getattr(getattr(user, "profile", None), "role", None) == Role.ADMIN:
        return references.filter(
            models.Q(visibility=ReferenceVisibility.SHARED)
            | models.Q(
                visibility=ReferenceVisibility.PRIVATE,
                owner__isnull=True,
            )
        )
    return references.filter(
        models.Q(visibility=ReferenceVisibility.SHARED)
        | models.Q(visibility=ReferenceVisibility.PRIVATE, owner=user)
    )


def next_reference_number():
    return (MasterVersion.objects.aggregate(value=Max("number"))["value"] or 0) + 1


@transaction.atomic
def create_reference(*, name, owner=None, visibility=ReferenceVisibility.SHARED):
    return MasterVersion.objects.create(
        number=next_reference_number(),
        name=name.strip(),
        visibility=visibility,
        owner=owner,
        status=(
            MasterStatus.PUBLISHED
            if visibility == ReferenceVisibility.SHARED
            else MasterStatus.DRAFT
        ),
    )


def latest_draft():
    return MasterVersion.objects.filter(status=MasterStatus.DRAFT).order_by("-number").first()

def latest_published():
    return MasterVersion.objects.filter(status=MasterStatus.PUBLISHED).order_by("-number").first()

def flatten_nodes(version, *, active_only=False):
    nodes = list(
        StructureNode.objects.filter(master_version=version).order_by("sort_order", "id")
    )
    children = defaultdict(list)
    for node in nodes:
        children[node.parent_id].append(node)

    result = []
    visited = set()

    def walk(parent_id, depth):
        for node in children[parent_id]:
            if node.id in visited:
                continue
            visited.add(node.id)
            if active_only and not node.active:
                continue
            result.append((node, depth))
            walk(node.id, depth + 1)

    walk(None, 0)

    if not active_only:
        for node in nodes:
            if node.id not in visited:
                result.append((node, 0))
    return result

def flatten_inspection_nodes(inspection, *, active_only=False):
    nodes = list(
        inspection.inspection_nodes.all().order_by("sort_order_snapshot", "id")
    )
    children = defaultdict(list)
    for node in nodes:
        children[node.parent_id].append(node)

    result = []
    visited = set()

    def walk(parent_id, depth):
        for node in children[parent_id]:
            if node.id in visited:
                continue
            visited.add(node.id)
            if active_only and node.scope_state != ScopeState.ACTIVE:
                continue
            result.append((node, depth))
            walk(node.id, depth + 1)

    walk(None, 0)
    if not active_only:
        for node in nodes:
            if node.id not in visited:
                result.append((node, 0))
    return result

@transaction.atomic
def create_draft_from_latest_published():
    existing = latest_draft()
    if existing:
        return existing, False

    max_number = MasterVersion.objects.aggregate(value=Max("number"))["value"] or 0
    draft = MasterVersion.objects.create(number=max_number + 1, status=MasterStatus.DRAFT)
    source = latest_published()
    if source is None:
        return draft, True

    def clone_children(parent_id=None, new_parent=None):
        source_nodes = StructureNode.objects.filter(
            master_version=source, parent_id=parent_id
        ).order_by("sort_order", "id")
        for old in source_nodes:
            new = StructureNode.objects.create(
                stable_id=old.stable_id,
                master_version=draft,
                parent=new_parent,
                title=old.title,
                description=old.description,
                inspectable=old.inspectable,
                sort_order=old.sort_order,
                active=old.active,
            )

            for spec in old.specifications.all().order_by("sort_order", "id"):
                SpecificationDefinition.objects.create(
                    stable_id=spec.stable_id,
                    node=new,
                    title=spec.title,
                    field_type=spec.field_type,
                    required=spec.required,
                    options=list(spec.options or []),
                    help_text=spec.help_text,
                    sort_order=spec.sort_order,
                    active=spec.active,
                )

            for item in old.items.all().order_by("sort_order", "id"):
                ChecklistItem.objects.create(
                    stable_id=item.stable_id,
                    node=new,
                    title=item.title,
                    guidance=item.guidance,
                    sort_order=item.sort_order,
                    active=item.active,
                )

            clone_children(old.id, new)

    clone_children()
    return draft, True

def _scope_origin_for_full_materialization(inspection):
    if inspection.scope_mode == InspectionScopeMode.LEGACY_FULL:
        return ScopeOrigin.LEGACY
    return ScopeOrigin.MANUAL

@transaction.atomic
def materialize_inspection(inspection):
    """
    Materialize the complete active reference.

    This remains available for historical/demo fixtures and explicit full-scope
    construction. New visit creation does not call it; selective visits start
    with an empty scope.
    """
    if inspection.inspection_nodes.exists():
        return False
    if inspection.master_version_id is None:
        return False

    origin = _scope_origin_for_full_materialization(inspection)

    def copy_children(parent_id=None, inspection_parent=None):
        source_nodes = StructureNode.objects.filter(
            master_version=inspection.master_version,
            parent_id=parent_id,
            active=True,
        ).order_by("sort_order", "id")
        for source in source_nodes:
            snapshot = InspectionNode.objects.create(
                inspection=inspection,
                source_node=source,
                parent=inspection_parent,
                title_snapshot=source.title,
                description_snapshot=source.description,
                inspectable_snapshot=source.inspectable,
                sort_order_snapshot=source.sort_order,
                scope_origin=origin,
                scope_state=ScopeState.ACTIVE,
                scope_role=ScopeRole.SELECTED,
            )

            for spec in source.specifications.filter(active=True).order_by("sort_order", "id"):
                SpecificationValue.objects.create(
                    inspection_node=snapshot,
                    source_specification=spec,
                    title_snapshot=spec.title,
                    field_type_snapshot=spec.field_type,
                    required_snapshot=spec.required,
                    options_snapshot=list(spec.options or []),
                    help_text_snapshot=spec.help_text,
                    sort_order_snapshot=spec.sort_order,
                    scope_origin=origin,
                    scope_state=ScopeState.ACTIVE,
                )

            for item in source.items.filter(active=True).order_by("sort_order", "id"):
                InspectionItemResult.objects.create(
                    inspection_node=snapshot,
                    source_item=item,
                    title_snapshot=item.title,
                    guidance_snapshot=item.guidance,
                    sort_order_snapshot=item.sort_order,
                    scope_origin=origin,
                    scope_state=ScopeState.ACTIVE,
                )

            copy_children(source.id, snapshot)

    copy_children()
    return True

def _mark_selective(inspection):
    if inspection.scope_mode != InspectionScopeMode.SELECTIVE:
        inspection.scope_mode = InspectionScopeMode.SELECTIVE
        inspection.save(update_fields=["scope_mode", "updated_at"])

def _source_chain(source_node):
    chain = []
    current = source_node
    version_id = source_node.master_version_id
    while current is not None:
        if current.master_version_id != version_id:
            raise ValidationError("مسار العنصر المرجعي غير صالح.")
        if not current.active:
            raise ValidationError("لا يمكن اختيار عنصر داخل فرع مرجعي غير نشط.")
        chain.append(current)
        current = current.parent
    chain.reverse()
    return chain

def _validate_source_node(inspection, source_node):
    if inspection.master_version_id is None:
        raise ValidationError("هذه الزيارة بدأت دون مرجع مصدر.")
    if source_node.master_version_id != inspection.master_version_id:
        raise ValidationError("العنصر لا ينتمي إلى إصدار المرجع المثبت لهذه الزيارة.")
    _source_chain(source_node)

def _activate_snapshot_node(
    inspection,
    source_node,
    *,
    origin=ScopeOrigin.MANUAL,
    role=ScopeRole.SELECTED,
    locked=False,
):
    _validate_source_node(inspection, source_node)
    parent_snapshot = None
    target_snapshot = None
    chain = _source_chain(source_node)

    for source in chain:
        is_target = source.id == source_node.id
        desired_role = role if is_target else ScopeRole.CONTEXT
        snapshot = InspectionNode.objects.filter(
            inspection=inspection,
            source_node=source,
        ).first()

        if snapshot is None:
            snapshot = InspectionNode.objects.create(
                inspection=inspection,
                source_node=source,
                parent=parent_snapshot,
                title_snapshot=source.title,
                description_snapshot=source.description,
                inspectable_snapshot=source.inspectable,
                sort_order_snapshot=source.sort_order,
                scope_origin=origin,
                scope_state=ScopeState.ACTIVE,
                scope_role=desired_role,
                scope_locked=locked if is_target else False,
            )
        else:
            updates = []
            reactivated = snapshot.scope_state != ScopeState.ACTIVE
            if snapshot.parent_id != (parent_snapshot.id if parent_snapshot else None):
                snapshot.parent = parent_snapshot
                updates.append("parent")
            if reactivated:
                snapshot.scope_state = ScopeState.ACTIVE
                updates.append("scope_state")
                if snapshot.scope_role != desired_role:
                    snapshot.scope_role = desired_role
                    updates.append("scope_role")
            if is_target and desired_role == ScopeRole.SELECTED and snapshot.scope_role != ScopeRole.SELECTED:
                snapshot.scope_role = ScopeRole.SELECTED
                updates.append("scope_role")
            if is_target and locked and not snapshot.scope_locked:
                snapshot.scope_locked = True
                updates.append("scope_locked")
            if is_target and snapshot.scope_origin != origin and (
                reactivated or desired_role == ScopeRole.SELECTED
            ):
                snapshot.scope_origin = origin
                updates.append("scope_origin")
            if updates:
                snapshot.save(update_fields=list(dict.fromkeys(updates)))

        parent_snapshot = snapshot
        if is_target:
            target_snapshot = snapshot

    return target_snapshot

@transaction.atomic
def add_scope_node(
    inspection,
    source_node,
    *,
    origin=ScopeOrigin.MANUAL,
    locked=False,
):
    snapshot = _activate_snapshot_node(
        inspection,
        source_node,
        origin=origin,
        role=ScopeRole.SELECTED,
        locked=locked,
    )
    _mark_selective(inspection)
    return snapshot

@transaction.atomic
def add_scope_specification(
    inspection,
    source_specification,
    *,
    origin=ScopeOrigin.MANUAL,
    locked=False,
    completion_required=False,
):
    if source_specification.node.master_version_id != inspection.master_version_id:
        raise ValidationError("الوصف لا ينتمي إلى إصدار المرجع المثبت لهذه الزيارة.")
    if not source_specification.active:
        raise ValidationError("لا يمكن اختيار وصف مرجعي غير نشط.")

    node_snapshot = _activate_snapshot_node(
        inspection,
        source_specification.node,
        origin=origin,
        role=ScopeRole.CONTEXT,
    )
    value = SpecificationValue.objects.filter(
        inspection_node=node_snapshot,
        source_specification=source_specification,
    ).first()
    if value is None:
        value = SpecificationValue.objects.create(
            inspection_node=node_snapshot,
            source_specification=source_specification,
            title_snapshot=source_specification.title,
            field_type_snapshot=source_specification.field_type,
            required_snapshot=source_specification.required,
            options_snapshot=list(source_specification.options or []),
            help_text_snapshot=source_specification.help_text,
            sort_order_snapshot=source_specification.sort_order,
            scope_origin=origin,
            scope_state=ScopeState.ACTIVE,
            scope_locked=locked,
            completion_required=completion_required,
        )
    else:
        updates = []
        if value.scope_state != ScopeState.ACTIVE:
            value.scope_state = ScopeState.ACTIVE
            value.scope_origin = origin
            updates.extend(["scope_state", "scope_origin"])
        if locked and not value.scope_locked:
            value.scope_locked = True
            updates.append("scope_locked")
        if completion_required and not value.completion_required:
            value.completion_required = True
            updates.append("completion_required")
        if updates:
            value.save(update_fields=list(dict.fromkeys(updates)))

    _mark_selective(inspection)
    return value

@transaction.atomic
def add_scope_item(
    inspection,
    source_item,
    *,
    origin=ScopeOrigin.MANUAL,
    locked=False,
    completion_required=False,
):
    if source_item.node.master_version_id != inspection.master_version_id:
        raise ValidationError("البند لا ينتمي إلى إصدار المرجع المثبت لهذه الزيارة.")
    if not source_item.active:
        raise ValidationError("لا يمكن اختيار بند مرجعي غير نشط.")

    node_snapshot = _activate_snapshot_node(
        inspection,
        source_item.node,
        origin=origin,
        role=ScopeRole.CONTEXT,
    )
    result = InspectionItemResult.objects.filter(
        inspection_node=node_snapshot,
        source_item=source_item,
    ).first()
    if result is None:
        result = InspectionItemResult.objects.create(
            inspection_node=node_snapshot,
            source_item=source_item,
            title_snapshot=source_item.title,
            guidance_snapshot=source_item.guidance,
            sort_order_snapshot=source_item.sort_order,
            scope_origin=origin,
            scope_state=ScopeState.ACTIVE,
            scope_locked=locked,
            completion_required=completion_required,
        )
    else:
        updates = []
        if result.scope_state != ScopeState.ACTIVE:
            result.scope_state = ScopeState.ACTIVE
            result.scope_origin = origin
            updates.extend(["scope_state", "scope_origin"])
        if locked and not result.scope_locked:
            result.scope_locked = True
            updates.append("scope_locked")
        if completion_required and not result.completion_required:
            result.completion_required = True
            updates.append("completion_required")
        if updates:
            result.save(update_fields=list(dict.fromkeys(updates)))

    _mark_selective(inspection)
    return result

@transaction.atomic
def add_scope_branch(
    inspection,
    source_node,
    *,
    origin=ScopeOrigin.MANUAL,
    locked=False,
    completion_required=False,
):
    _validate_source_node(inspection, source_node)

    def add_recursive(node):
        add_scope_node(inspection, node, origin=origin, locked=locked)
        for spec in node.specifications.filter(active=True).order_by("sort_order", "id"):
            add_scope_specification(
                inspection,
                spec,
                origin=origin,
                locked=locked,
                completion_required=completion_required,
            )
        for item in node.items.filter(active=True).order_by("sort_order", "id"):
            add_scope_item(
                inspection,
                item,
                origin=origin,
                locked=locked,
                completion_required=completion_required,
            )
        for child in node.children.filter(active=True).order_by("sort_order", "id"):
            add_recursive(child)

    add_recursive(source_node)
    _mark_selective(inspection)

def _active_dependents(node):
    if node.children.filter(scope_state=ScopeState.ACTIVE).exists():
        return True
    if node.specification_values.filter(scope_state=ScopeState.ACTIVE).exists():
        return True
    if node.item_results.filter(scope_state=ScopeState.ACTIVE).exists():
        return True
    return False

def _prune_context_chain(node):
    current = node
    while current is not None:
        if current.scope_state != ScopeState.ACTIVE:
            current = current.parent
            continue
        if current.scope_role != ScopeRole.CONTEXT or current.scope_locked:
            break
        if _active_dependents(current):
            break
        current.scope_state = ScopeState.EXCLUDED
        current.save(update_fields=["scope_state"])
        current = current.parent

def _inspection_node_subtree(node):
    nodes = []
    frontier = [node]
    while frontier:
        current = frontier.pop(0)
        nodes.append(current)
        frontier.extend(
            list(current.children.all().order_by("sort_order_snapshot", "id"))
        )
    return nodes

@transaction.atomic
def exclude_scope_node(node):
    if node.scope_state == ScopeState.EXCLUDED:
        return False

    subtree = _inspection_node_subtree(node)
    if any(candidate.scope_locked for candidate in subtree):
        raise ValidationError("يتضمن هذا الفرع عنصرًا مقيدًا لا يمكن إخراجه من النطاق.")
    for candidate in subtree:
        if candidate.specification_values.filter(
            scope_state=ScopeState.ACTIVE,
            scope_locked=True,
        ).exists():
            raise ValidationError("يتضمن هذا الفرع وصفًا مقيدًا لا يمكن إخراجه من النطاق.")
        if candidate.item_results.filter(
            scope_state=ScopeState.ACTIVE,
            scope_locked=True,
        ).exists():
            raise ValidationError("يتضمن هذا الفرع بندًا مقيدًا لا يمكن إخراجه من النطاق.")

    for candidate in subtree:
        candidate.specification_values.filter(
            scope_state=ScopeState.ACTIVE
        ).update(scope_state=ScopeState.EXCLUDED)
        candidate.item_results.filter(
            scope_state=ScopeState.ACTIVE
        ).update(scope_state=ScopeState.EXCLUDED)
        if candidate.scope_state != ScopeState.EXCLUDED:
            candidate.scope_state = ScopeState.EXCLUDED
            candidate.save(update_fields=["scope_state"])

    _mark_selective(node.inspection)
    _prune_context_chain(node.parent)
    return True

@transaction.atomic
def exclude_scope_specification(value):
    if value.scope_state == ScopeState.EXCLUDED:
        return False
    if value.scope_locked:
        raise ValidationError("هذا الوصف مقيد ولا يمكن إخراجه من النطاق.")
    value.scope_state = ScopeState.EXCLUDED
    value.save(update_fields=["scope_state"])
    _mark_selective(value.inspection_node.inspection)
    _prune_context_chain(value.inspection_node)
    return True

@transaction.atomic
def exclude_scope_item(result):
    if result.scope_state == ScopeState.EXCLUDED:
        return False
    if result.scope_locked:
        raise ValidationError("هذا البند مقيد ولا يمكن إخراجه من النطاق.")
    result.scope_state = ScopeState.EXCLUDED
    result.save(update_fields=["scope_state"])
    _mark_selective(result.inspection_node.inspection)
    _prune_context_chain(result.inspection_node)
    return True

def active_item_results(inspection):
    return InspectionItemResult.objects.filter(
        inspection_node__inspection=inspection,
        inspection_node__scope_state=ScopeState.ACTIVE,
        scope_state=ScopeState.ACTIVE,
    )

def active_specification_values(inspection):
    return SpecificationValue.objects.filter(
        inspection_node__inspection=inspection,
        inspection_node__scope_state=ScopeState.ACTIVE,
        scope_state=ScopeState.ACTIVE,
    )

def incomplete_required_scope_count(inspection):
    missing = 0
    for value in active_specification_values(inspection).filter(completion_required=True):
        if value.value is None or value.value == "" or value.value == [] or value.value == {}:
            missing += 1
    missing += active_item_results(inspection).filter(
        completion_required=True,
        status="UNCHECKED",
    ).count()
    return missing

def scope_reference_rows(inspection):
    if inspection.master_version_id is None:
        return []

    node_snapshots = {
        snapshot.source_node_id: snapshot
        for snapshot in inspection.inspection_nodes.exclude(source_node=None)
    }
    spec_snapshots = {
        value.source_specification_id: value
        for value in SpecificationValue.objects.filter(
            inspection_node__inspection=inspection,
            source_specification__isnull=False,
        )
    }
    item_snapshots = {
        result.source_item_id: result
        for result in InspectionItemResult.objects.filter(
            inspection_node__inspection=inspection,
            source_item__isnull=False,
        )
    }

    rows = []
    for node, depth in flatten_nodes(inspection.master_version, active_only=True):
        rows.append(
            {
                "node": node,
                "depth": depth,
                "snapshot": node_snapshots.get(node.id),
                "specifications": [
                    {
                        "definition": spec,
                        "snapshot": spec_snapshots.get(spec.id),
                    }
                    for spec in node.specifications.filter(active=True).order_by(
                        "sort_order", "id"
                    )
                ],
                "items": [
                    {
                        "definition": item,
                        "snapshot": item_snapshots.get(item.id),
                    }
                    for item in node.items.filter(active=True).order_by("sort_order", "id")
                ],
            }
        )
    return rows

def descendant_ids(node):
    found = set()
    frontier = [node.id]
    while frontier:
        ids = list(
            StructureNode.objects.filter(parent_id__in=frontier)
            .exclude(id__in=found)
            .values_list("id", flat=True)
        )
        if not ids:
            break
        found.update(ids)
        frontier = ids
    return found
