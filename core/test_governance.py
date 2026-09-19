from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .governance import (
    approve_proposal,
    merge_institution_proposal,
    reject_proposal,
)
from .models import (
    ChecklistItem,
    FieldType,
    Inspection,
    InspectionStatus,
    Institution,
    InstitutionVerificationStatus,
    MasterStatus,
    MasterVersion,
    Proposal,
    ProposalStatus,
    ProposalType,
    ScopeOrigin,
    SpecificationDefinition,
    StructureNode,
)
from .services import (
    create_draft_from_latest_published,
    materialize_inspection,
)

User = get_user_model()

class Gate5GovernanceTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user("g5-inspector", password="test-pass-123")
        self.other = User.objects.create_user("g5-other", password="test-pass-123")
        self.admin = User.objects.create_superuser("g5-admin", "admin@example.com", "test-pass-123")
        self.institution = Institution.objects.create(name="مؤسسة أصلية")
        self.published = MasterVersion.objects.create(number=1, status=MasterStatus.PUBLISHED)
        self.root = StructureNode.objects.create(
            master_version=self.published,
            title="المجال الأصلي",
            sort_order=1,
        )
        self.spec = SpecificationDefinition.objects.create(
            node=self.root,
            title="عدد الموظفين",
            field_type=FieldType.NUMBER,
            sort_order=1,
        )
        self.item = ChecklistItem.objects.create(
            node=self.root,
            title="بند أصلي",
            guidance="توجيه أصلي",
            sort_order=1,
        )
        self.inspection = Inspection.objects.create(
            institution=self.institution,
            inspector=self.inspector,
            master_version=self.published,
            visit_date=date(2026, 9, 18),
        )
        materialize_inspection(self.inspection)
        self.snap_root = self.inspection.inspection_nodes.get(source_node=self.root)

    def login_inspector(self):
        self.client.login(username="g5-inspector", password="test-pass-123")

    def login_admin(self):
        self.client.login(username="g5-admin", password="test-pass-123")

    def test_draft_clone_preserves_stable_ids(self):
        draft, created = create_draft_from_latest_published()
        self.assertTrue(created)
        clone = draft.nodes.get(title=self.root.title)
        self.assertEqual(clone.stable_id, self.root.stable_id)
        self.assertEqual(clone.specifications.get().stable_id, self.spec.stable_id)
        self.assertEqual(clone.items.get().stable_id, self.item.stable_id)

    def test_local_node_is_immediately_available_and_creates_one_proposal(self):
        self.login_inspector()
        response = self.client.post(
            reverse("local_node_add", args=[self.inspection.pk, self.snap_root.pk]),
            {"title": "فرع ميداني", "description": "ظهر في الواقع", "inspectable": "on"},
        )
        local = self.inspection.inspection_nodes.get(title_snapshot="فرع ميداني")
        self.assertRedirects(
            response,
            reverse("inspection_node_prepare", args=[self.inspection.pk, local.pk]),
        )
        self.assertEqual(local.scope_origin, ScopeOrigin.LOCAL)
        self.assertEqual(local.parent, self.snap_root)
        proposal = Proposal.objects.get(
            proposal_type=ProposalType.NODE,
            source_local_id=local.id,
        )
        self.assertEqual(proposal.status, ProposalStatus.PENDING)
        self.assertEqual(
            proposal.payload["target_node_stable_id"],
            str(self.root.stable_id),
        )
        self.assertFalse(
            StructureNode.objects.filter(
                master_version=self.published, title="فرع ميداني"
            ).exists()
        )

    def test_local_spec_and_item_are_immediately_usable_and_proposed(self):
        self.login_inspector()
        self.client.post(
            reverse("local_spec_add", args=[self.inspection.pk, self.snap_root.pk]),
            {
                "title": "نوع المقر",
                "field_type": FieldType.SINGLE_SELECT,
                "required": "",
                "options_text": "ملكية\nإيجار",
                "help_text": "حدد النوع",
            },
        )
        self.client.post(
            reverse("local_item_add", args=[self.inspection.pk, self.snap_root.pk]),
            {"title": "بند ميداني", "guidance": "تحقق ميدانيًا"},
        )
        spec = self.snap_root.specification_values.get(title_snapshot="نوع المقر")
        item = self.snap_root.item_results.get(title_snapshot="بند ميداني")
        self.assertEqual(spec.scope_origin, ScopeOrigin.LOCAL)
        self.assertEqual(spec.options_snapshot, ["ملكية", "إيجار"])
        self.assertEqual(item.scope_origin, ScopeOrigin.LOCAL)
        self.assertEqual(
            Proposal.objects.filter(source_inspection=self.inspection).count(),
            2,
        )
        self.assertTrue(
            Proposal.objects.filter(
                proposal_type=ProposalType.SPECIFICATION,
                source_local_id=spec.id,
            ).exists()
        )
        self.assertTrue(
            Proposal.objects.filter(
                proposal_type=ProposalType.ITEM,
                source_local_id=item.id,
            ).exists()
        )

    def test_completed_inspection_rejects_local_additions(self):
        self.inspection.status = InspectionStatus.COMPLETED
        self.inspection.save(update_fields=["status"])
        self.login_inspector()
        response = self.client.post(
            reverse("local_item_add", args=[self.inspection.pk, self.snap_root.pk]),
            {"title": "لا يجب إضافته", "guidance": ""},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            self.snap_root.item_results.filter(title_snapshot="لا يجب إضافته").exists()
        )

    def test_inspector_cannot_access_admin_governance_or_reference_builder(self):
        self.login_inspector()
        self.assertEqual(self.client.get(reverse("proposal_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("builder_home")).status_code, 403)

    def test_admin_can_edit_payload_then_approve_local_item_into_draft_only(self):
        self.login_inspector()
        self.client.post(
            reverse("local_item_add", args=[self.inspection.pk, self.snap_root.pk]),
            {"title": "عنوان أولي", "guidance": "توجيه"},
        )
        local_item = self.snap_root.item_results.get(title_snapshot="عنوان أولي")
        proposal = Proposal.objects.get(
            proposal_type=ProposalType.ITEM,
            source_local_id=local_item.id,
        )

        self.login_admin()
        response = self.client.post(
            reverse("proposal_detail", args=[proposal.pk]),
            {
                "title": "عنوان معتمد معدل",
                "guidance": "توجيه معدل",
                "sort_order": proposal.payload["sort_order"],
                "resolution_note": "تمت المراجعة",
                "action": "approve",
            },
        )
        self.assertRedirects(response, reverse("proposal_detail", args=[proposal.pk]))
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, ProposalStatus.APPROVED)
        self.assertEqual(proposal.payload["title"], "عنوان معتمد معدل")
        self.assertEqual(proposal.resolution_note, "تمت المراجعة")

        draft = MasterVersion.objects.get(status=MasterStatus.DRAFT)
        approved = ChecklistItem.objects.get(
            node__master_version=draft,
            title="عنوان معتمد معدل",
        )
        self.assertEqual(approved.guidance, "توجيه معدل")

        local_item.refresh_from_db()
        self.assertEqual(local_item.title_snapshot, "عنوان أولي")
        self.assertEqual(local_item.scope_origin, ScopeOrigin.LOCAL)

    def test_proposal_approval_is_idempotent(self):
        local = self.snap_root.item_results.create(
            title_snapshot="بند محلي",
            guidance_snapshot="",
            scope_origin=ScopeOrigin.LOCAL,
            sort_order_snapshot=20,
        )
        proposal = Proposal.objects.create(
            proposal_type=ProposalType.ITEM,
            source_inspection=self.inspection,
            source_local_id=local.id,
            proposed_by=self.inspector,
            payload={
                "target_node_stable_id": str(self.root.stable_id),
                "title": "بند محلي",
                "guidance": "",
                "sort_order": 20,
            },
        )
        first, changed = approve_proposal(
            proposal, self.admin, dict(proposal.payload), "اعتماد"
        )
        self.assertTrue(changed)
        second, changed_again = approve_proposal(
            first, self.admin, dict(first.payload), "محاولة ثانية"
        )
        self.assertFalse(changed_again)
        draft = MasterVersion.objects.get(status=MasterStatus.DRAFT)
        self.assertEqual(
            ChecklistItem.objects.filter(
                node__master_version=draft, title="بند محلي"
            ).count(),
            1,
        )

    def test_child_local_node_requires_parent_approval_first(self):
        parent_local = self.snap_root.children.create(
            inspection=self.inspection,
            title_snapshot="أب محلي",
            scope_origin=ScopeOrigin.LOCAL,
            sort_order_snapshot=20,
        )
        parent_proposal = Proposal.objects.create(
            proposal_type=ProposalType.NODE,
            source_inspection=self.inspection,
            source_local_id=parent_local.id,
            proposed_by=self.inspector,
            payload={
                "target_node_stable_id": str(self.root.stable_id),
                "title": "أب محلي",
                "description": "",
                "inspectable": True,
                "sort_order": 20,
            },
        )
        child_local = parent_local.children.create(
            inspection=self.inspection,
            title_snapshot="ابن محلي",
            scope_origin=ScopeOrigin.LOCAL,
            sort_order_snapshot=10,
        )
        child_proposal = Proposal.objects.create(
            proposal_type=ProposalType.NODE,
            source_inspection=self.inspection,
            source_local_id=child_local.id,
            proposed_by=self.inspector,
            payload={
                "target_local_node_id": parent_local.id,
                "title": "ابن محلي",
                "description": "",
                "inspectable": True,
                "sort_order": 10,
            },
        )

        with self.assertRaises(ValidationError):
            approve_proposal(
                child_proposal, self.admin, dict(child_proposal.payload)
            )

        approve_proposal(parent_proposal, self.admin, dict(parent_proposal.payload))
        approve_proposal(child_proposal, self.admin, dict(child_proposal.payload))
        child_proposal.refresh_from_db()
        draft = MasterVersion.objects.get(status=MasterStatus.DRAFT)
        approved_child = StructureNode.objects.get(
            master_version=draft,
            stable_id=child_proposal.resolution_data["stable_id"],
        )
        self.assertEqual(approved_child.parent.title, "أب محلي")

    def test_rejecting_local_item_keeps_it_in_source_inspection(self):
        local = self.snap_root.item_results.create(
            title_snapshot="يبقى في الزيارة",
            guidance_snapshot="",
            scope_origin=ScopeOrigin.LOCAL,
            sort_order_snapshot=30,
        )
        proposal = Proposal.objects.create(
            proposal_type=ProposalType.ITEM,
            source_inspection=self.inspection,
            source_local_id=local.id,
            proposed_by=self.inspector,
            payload={
                "target_node_stable_id": str(self.root.stable_id),
                "title": local.title_snapshot,
                "guidance": "",
                "sort_order": 30,
            },
        )
        reject_proposal(proposal, self.admin, "خاص بهذه الزيارة")
        proposal.refresh_from_db()
        local.refresh_from_db()
        self.assertEqual(proposal.status, ProposalStatus.REJECTED)
        self.assertEqual(local.scope_origin, ScopeOrigin.LOCAL)
        self.assertEqual(local.title_snapshot, "يبقى في الزيارة")

    def test_rejected_institution_is_hidden_but_old_inspection_keeps_reference(self):
        self.login_inspector()
        self.client.post(
            reverse("institution_create"),
            {"name": "مؤسسة مؤقتة", "institution_type": "CFPA", "commune": "تبسة"},
        )
        local = Institution.objects.get(name="مؤسسة مؤقتة")
        old_visit = Inspection.objects.create(
            institution=local,
            inspector=self.inspector,
            master_version=self.published,
            visit_date=date(2026, 9, 19),
        )
        proposal = Proposal.objects.get(
            proposal_type=ProposalType.INSTITUTION,
            source_local_id=local.id,
        )
        reject_proposal(proposal, self.admin, "ليست مؤسسة مستقلة")
        local.refresh_from_db()
        old_visit.refresh_from_db()
        self.assertEqual(local.verification_status, InstitutionVerificationStatus.REJECTED)
        self.assertFalse(local.active)
        self.assertEqual(old_visit.institution_id, local.id)

        response = self.client.get(reverse("institution_list"))
        self.assertNotContains(response, "مؤسسة مؤقتة")

    def test_institution_merge_records_target_without_rewriting_old_visit(self):
        target = Institution.objects.create(name="المؤسسة المعتمدة")
        local = Institution.objects.create(
            name="اسم مكرر",
            created_by=self.inspector,
            verification_status=InstitutionVerificationStatus.PENDING,
        )
        visit = Inspection.objects.create(
            institution=local,
            inspector=self.inspector,
            master_version=self.published,
            visit_date=date(2026, 9, 19),
        )
        proposal = Proposal.objects.create(
            proposal_type=ProposalType.INSTITUTION,
            source_local_id=local.id,
            proposed_by=self.inspector,
            payload={
                "institution_id": local.id,
                "name": local.name,
                "institution_type": "",
                "commune": "",
            },
        )
        merge_institution_proposal(proposal, self.admin, target, "مكرر")
        proposal.refresh_from_db()
        local.refresh_from_db()
        visit.refresh_from_db()
        self.assertEqual(proposal.status, ProposalStatus.MERGED)
        self.assertEqual(
            proposal.resolution_data["merged_into_institution_id"],
            target.id,
        )
        self.assertFalse(local.active)
        self.assertEqual(visit.institution_id, local.id)


