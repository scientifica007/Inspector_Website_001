from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    ChecklistItem,
    MasterStatus,
    MasterVersion,
    ReferenceSubmission,
    ReferenceSubmissionStatus,
    ReferenceVisibility,
    SpecificationDefinition,
    StructureNode,
)
from .services import next_reference_number


def serialize_reference(reference):
    def serialize_node(node):
        return {
            "stable_id": str(node.stable_id),
            "title": node.title,
            "description": node.description,
            "inspectable": node.inspectable,
            "sort_order": node.sort_order,
            "active": node.active,
            "descriptions": [
                {
                    "stable_id": str(spec.stable_id),
                    "title": spec.title,
                    "field_type": spec.field_type,
                    "required": spec.required,
                    "options": list(spec.options or []),
                    "help_text": spec.help_text,
                    "sort_order": spec.sort_order,
                    "active": spec.active,
                }
                for spec in node.specifications.all().order_by("sort_order", "id")
            ],
            "items": [
                {
                    "stable_id": str(item.stable_id),
                    "title": item.title,
                    "guidance": item.guidance,
                    "sort_order": item.sort_order,
                    "active": item.active,
                }
                for item in node.items.all().order_by("sort_order", "id")
            ],
            "children": [
                serialize_node(child)
                for child in node.children.all().order_by("sort_order", "id")
            ],
        }

    roots = reference.nodes.filter(parent__isnull=True).order_by("sort_order", "id")
    return {
        "name": reference.name,
        "nodes": [serialize_node(node) for node in roots],
    }


def _create_tree(reference, snapshot, *, preserve_stable_ids=False):
    def create_node(data, parent=None):
        node_kwargs = {
            "master_version": reference,
            "parent": parent,
            "title": data["title"],
            "description": data.get("description", ""),
            "inspectable": data.get("inspectable", True),
            "sort_order": data.get("sort_order", 0),
            "active": data.get("active", True),
        }
        if preserve_stable_ids and data.get("stable_id"):
            node_kwargs["stable_id"] = data["stable_id"]
        node = StructureNode.objects.create(**node_kwargs)

        for spec in data.get("descriptions", []):
            spec_kwargs = {
                "node": node,
                "title": spec["title"],
                "field_type": spec["field_type"],
                "required": spec.get("required", False),
                "options": list(spec.get("options", [])),
                "help_text": spec.get("help_text", ""),
                "sort_order": spec.get("sort_order", 0),
                "active": spec.get("active", True),
            }
            if preserve_stable_ids and spec.get("stable_id"):
                spec_kwargs["stable_id"] = spec["stable_id"]
            SpecificationDefinition.objects.create(**spec_kwargs)

        for item in data.get("items", []):
            item_kwargs = {
                "node": node,
                "title": item["title"],
                "guidance": item.get("guidance", ""),
                "sort_order": item.get("sort_order", 0),
                "active": item.get("active", True),
            }
            if preserve_stable_ids and item.get("stable_id"):
                item_kwargs["stable_id"] = item["stable_id"]
            ChecklistItem.objects.create(**item_kwargs)

        for child in data.get("children", []):
            create_node(child, node)
        return node

    for root in snapshot.get("nodes", []):
        create_node(root)


@transaction.atomic
def create_reference_from_snapshot(
    *, snapshot, name, visibility, owner=None, preserve_stable_ids=False
):
    reference = MasterVersion.objects.create(
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
    _create_tree(
        reference,
        snapshot,
        preserve_stable_ids=preserve_stable_ids,
    )
    return reference


@transaction.atomic
def freeze_reference_for_inspection(source):
    """
    Create an internal reference snapshot for one inspection.
    Stable IDs are preserved while database rows are independent.
    """
    snapshot = serialize_reference(source)
    return create_reference_from_snapshot(
        snapshot=snapshot,
        name=source.name,
        visibility=ReferenceVisibility.SNAPSHOT,
        owner=None,
        preserve_stable_ids=True,
    )


@transaction.atomic
def clone_as_private(source, user, *, name=None):
    snapshot = serialize_reference(source)
    return create_reference_from_snapshot(
        snapshot=snapshot,
        name=(name or f"نسخة من {source.name}"),
        visibility=ReferenceVisibility.PRIVATE,
        owner=user,
    )


@transaction.atomic
def submit_private_reference(reference, user):
    if reference.visibility != ReferenceVisibility.PRIVATE or reference.owner_id != user.id:
        raise ValidationError("يمكن اقتراح مرجع خاص تملكه أنت فقط.")

    pending = ReferenceSubmission.objects.filter(
        source_reference=reference,
        submitted_by=user,
        status=ReferenceSubmissionStatus.PENDING,
    ).first()
    if pending:
        return pending, False

    submission = ReferenceSubmission.objects.create(
        source_reference=reference,
        submitted_by=user,
        source_name_snapshot=reference.name,
        snapshot=serialize_reference(reference),
    )
    return submission, True


@transaction.atomic
def withdraw_submission(submission, user):
    submission = ReferenceSubmission.objects.select_for_update().get(pk=submission.pk)
    if submission.submitted_by_id != user.id:
        raise ValidationError("لا يمكنك سحب اقتراح لا تملكه.")
    if submission.status != ReferenceSubmissionStatus.PENDING:
        return submission, False
    submission.status = ReferenceSubmissionStatus.WITHDRAWN
    submission.resolved_by = user
    submission.resolved_at = timezone.now()
    submission.resolution_note = "سحب صاحب المرجع الاقتراح."
    submission.save(
        update_fields=["status", "resolved_by", "resolved_at", "resolution_note"]
    )
    return submission, True


@transaction.atomic
def approve_reference_submission(submission, admin, *, shared_name, note=""):
    submission = ReferenceSubmission.objects.select_for_update().get(pk=submission.pk)
    if submission.status != ReferenceSubmissionStatus.PENDING:
        return submission, False

    reference = create_reference_from_snapshot(
        snapshot=submission.snapshot,
        name=shared_name,
        visibility=ReferenceVisibility.SHARED,
        owner=None,
    )
    submission.status = ReferenceSubmissionStatus.APPROVED
    submission.resulting_reference = reference
    submission.resolved_by = admin
    submission.resolved_at = timezone.now()
    submission.resolution_note = note or ""
    submission.save(
        update_fields=[
            "status",
            "resulting_reference",
            "resolved_by",
            "resolved_at",
            "resolution_note",
        ]
    )
    return submission, True


@transaction.atomic
def reject_reference_submission(submission, admin, *, note=""):
    submission = ReferenceSubmission.objects.select_for_update().get(pk=submission.pk)
    if submission.status != ReferenceSubmissionStatus.PENDING:
        return submission, False
    submission.status = ReferenceSubmissionStatus.REJECTED
    submission.resolved_by = admin
    submission.resolved_at = timezone.now()
    submission.resolution_note = note or ""
    submission.save(
        update_fields=["status", "resolved_by", "resolved_at", "resolution_note"]
    )
    return submission, True
