from collections import defaultdict

from django.db import transaction
from django.db.models import Max

from .models import (
    ChecklistItem,
    InspectionItemResult,
    InspectionNode,
    MasterStatus,
    MasterVersion,
    SpecificationDefinition,
    SpecificationValue,
    StructureNode,
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

def flatten_inspection_nodes(inspection):
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
            result.append((node, depth))
            walk(node.id, depth + 1)

    walk(None, 0)
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

@transaction.atomic
def materialize_inspection(inspection):
    if inspection.inspection_nodes.exists():
        return False

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
                sort_order_snapshot=source.sort_order,
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
                )

            for item in source.items.filter(active=True).order_by("sort_order", "id"):
                InspectionItemResult.objects.create(
                    inspection_node=snapshot,
                    source_item=item,
                    title_snapshot=item.title,
                    guidance_snapshot=item.guidance,
                    sort_order_snapshot=item.sort_order,
                )

            copy_children(source.id, snapshot)

    copy_children()
    return True

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
