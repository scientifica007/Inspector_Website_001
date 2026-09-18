from collections import defaultdict
from django.db import transaction
from django.db.models import Max

from .models import (
    ChecklistItem,
    MasterStatus,
    MasterVersion,
    SpecificationDefinition,
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
                # Deactivating a branch hides the whole branch from inspector-facing preview.
                continue
            result.append((node, depth))
            walk(node.id, depth + 1)

    walk(None, 0)

    # In builder mode, malformed/orphaned records are surfaced rather than silently hidden.
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
                    node=new,
                    title=item.title,
                    guidance=item.guidance,
                    sort_order=item.sort_order,
                    active=item.active,
                )

            clone_children(old.id, new)

    clone_children()
    return draft, True

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
