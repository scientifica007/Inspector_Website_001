from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from .models import (
    ChecklistItem,
    Institution,
    InstitutionVerificationStatus,
    MasterStatus,
    MasterVersion,
    Proposal,
    ProposalStatus,
    ProposalType,
    SpecificationDefinition,
    StructureNode,
)
from .services import create_draft_from_latest_published

def _target_draft_node(proposal, draft):
    payload = proposal.payload or {}
    if proposal.proposal_type == ProposalType.NODE and payload.get("target_root"):
        return None

    stable_id = payload.get("target_node_stable_id")
    if stable_id:
        try:
            return StructureNode.objects.get(master_version=draft, stable_id=stable_id)
        except StructureNode.DoesNotExist as exc:
            raise ValidationError("العنصر المستهدف غير موجود في المسودة الحالية.") from exc

    local_id = payload.get("target_local_node_id")
    if local_id:
        parent_proposal = Proposal.objects.filter(
            proposal_type=ProposalType.NODE,
            source_inspection=proposal.source_inspection,
            source_local_id=local_id,
            status__in=[ProposalStatus.APPROVED, ProposalStatus.MERGED],
        ).order_by("-resolved_at", "-id").first()
        if not parent_proposal:
            raise ValidationError(
                "يجب اعتماد الفرع المحلي الأب أولًا قبل اعتماد هذا الاقتراح."
            )
        stable = (parent_proposal.resolution_data or {}).get("stable_id")
        if not stable:
            raise ValidationError("لا يمكن تحديد الفرع المعتمد الذي يقابل الأب المحلي.")
        try:
            return StructureNode.objects.get(master_version=draft, stable_id=stable)
        except StructureNode.DoesNotExist as exc:
            raise ValidationError("الفرع الأب المعتمد غير موجود في المسودة الحالية.") from exc

    raise ValidationError("الاقتراح لا يحتوي على مرجع للعنصر المستهدف.")

def _resolve(proposal, user, status, note="", resolution_data=None):
    proposal.status = status
    proposal.resolution_note = note or ""
    proposal.resolution_data = resolution_data or {}
    proposal.resolved_by = user
    proposal.resolved_at = timezone.now()
    proposal.save(
        update_fields=[
            "status",
            "resolution_note",
            "resolution_data",
            "resolved_by",
            "resolved_at",
            "payload",
        ]
    )

@transaction.atomic
def approve_proposal(proposal, user, payload, note=""):
    proposal = Proposal.objects.select_for_update().get(pk=proposal.pk)
    if proposal.status != ProposalStatus.PENDING:
        return proposal, False

    proposal.payload = payload

    if proposal.proposal_type == ProposalType.INSTITUTION:
        institution = Institution.objects.select_for_update().get(
            pk=payload["institution_id"]
        )
        institution.name = payload["name"]
        institution.institution_type = payload.get("institution_type", "")
        institution.commune = payload.get("commune", "")
        institution.verification_status = InstitutionVerificationStatus.VERIFIED
        institution.active = True
        institution.save(
            update_fields=[
                "name",
                "institution_type",
                "commune",
                "verification_status",
                "active",
            ]
        )
        _resolve(
            proposal,
            user,
            ProposalStatus.APPROVED,
            note,
            {"institution_id": institution.id},
        )
        return proposal, True

    draft, _ = create_draft_from_latest_published()
    target = _target_draft_node(proposal, draft)

    if proposal.proposal_type == ProposalType.NODE:
        obj = StructureNode.objects.create(
            master_version=draft,
            parent=target,
            title=payload["title"],
            description=payload.get("description", ""),
            inspectable=payload.get("inspectable", True),
            sort_order=payload.get("sort_order", 0),
            active=True,
        )
    elif proposal.proposal_type == ProposalType.SPECIFICATION:
        if target is None:
            raise ValidationError("الوصف يحتاج إلى عنصر مرجعي مستهدف.")
        obj = SpecificationDefinition.objects.create(
            node=target,
            title=payload["title"],
            field_type=payload["field_type"],
            required=payload.get("required", False),
            options=list(payload.get("options", [])),
            help_text=payload.get("help_text", ""),
            sort_order=payload.get("sort_order", 0),
            active=True,
        )
    elif proposal.proposal_type == ProposalType.ITEM:
        if target is None:
            raise ValidationError("بند التفتيش يحتاج إلى عنصر مرجعي مستهدف.")
        obj = ChecklistItem.objects.create(
            node=target,
            title=payload["title"],
            guidance=payload.get("guidance", ""),
            sort_order=payload.get("sort_order", 0),
            active=True,
        )
    else:
        raise ValidationError("نوع اقتراح غير مدعوم.")

    _resolve(
        proposal,
        user,
        ProposalStatus.APPROVED,
        note,
        {
            "object_id": obj.id,
            "stable_id": str(obj.stable_id),
            "draft_version": draft.number,
        },
    )
    return proposal, True

@transaction.atomic
def reject_proposal(proposal, user, note=""):
    proposal = Proposal.objects.select_for_update().get(pk=proposal.pk)
    if proposal.status != ProposalStatus.PENDING:
        return proposal, False

    if proposal.proposal_type == ProposalType.INSTITUTION:
        institution_id = (proposal.payload or {}).get("institution_id")
        if institution_id:
            Institution.objects.filter(pk=institution_id).update(
                verification_status=InstitutionVerificationStatus.REJECTED,
                active=False,
            )

    _resolve(proposal, user, ProposalStatus.REJECTED, note, {})
    return proposal, True

@transaction.atomic
def merge_institution_proposal(proposal, user, target, note=""):
    proposal = Proposal.objects.select_for_update().get(pk=proposal.pk)
    if proposal.status != ProposalStatus.PENDING:
        return proposal, False
    if proposal.proposal_type != ProposalType.INSTITUTION:
        raise ValidationError("الدمج متاح لاقتراحات المؤسسات فقط.")

    institution_id = (proposal.payload or {}).get("institution_id")
    if institution_id:
        Institution.objects.filter(pk=institution_id).update(
            verification_status=InstitutionVerificationStatus.REJECTED,
            active=False,
        )

    _resolve(
        proposal,
        user,
        ProposalStatus.MERGED,
        note,
        {"merged_into_institution_id": target.id},
    )
    return proposal, True

def validate_master_tree(version):
    nodes = list(
        StructureNode.objects.filter(master_version=version).values(
            "id", "parent_id", "stable_id"
        )
    )
    ids = {row["id"] for row in nodes}
    parent_by_id = {row["id"]: row["parent_id"] for row in nodes}

    for row in nodes:
        parent_id = row["parent_id"]
        if parent_id is not None and parent_id not in ids:
            raise ValidationError("يوجد عنصر أب خارج نسخة المرجع الحالية.")

    for node_id in ids:
        seen = set()
        current = node_id
        while current is not None:
            if current in seen:
                raise ValidationError("يوجد مسار دائري داخل شجرة المرجع.")
            seen.add(current)
            current = parent_by_id.get(current)

    duplicate_nodes = (
        StructureNode.objects.filter(master_version=version)
        .values("stable_id")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
        .exists()
    )
    duplicate_specs = (
        SpecificationDefinition.objects.filter(node__master_version=version)
        .values("stable_id")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
        .exists()
    )
    duplicate_items = (
        ChecklistItem.objects.filter(node__master_version=version)
        .values("stable_id")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
        .exists()
    )
    if duplicate_nodes or duplicate_specs or duplicate_items:
        raise ValidationError("توجد هوية مرجعية مكررة داخل النسخة نفسها.")

@transaction.atomic
def publish_draft(draft):
    draft = MasterVersion.objects.select_for_update().get(pk=draft.pk)
    if draft.status != MasterStatus.DRAFT:
        raise ValidationError("يمكن نشر نسخة مسودة فقط.")

    validate_master_tree(draft)
    MasterVersion.objects.select_for_update().filter(
        status=MasterStatus.PUBLISHED
    ).exclude(pk=draft.pk).update(status=MasterStatus.ARCHIVED)

    draft.status = MasterStatus.PUBLISHED
    draft.published_at = timezone.now()
    draft.save(update_fields=["status", "published_at"])
    return draft
