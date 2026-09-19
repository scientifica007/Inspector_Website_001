from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .governance import (
    merge_institution_proposal,
    reject_proposal,
)
from .models import (
    ChecklistItem,
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
    StructureNode,
)
from .services import materialize_inspection

User = get_user_model()


class Gate5GovernanceTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user(
            "g5-inspector", password="test-pass-123"
        )
        self.other = User.objects.create_user(
            "g5-other", password="test-pass-123"
        )
        self.admin = User.objects.create_superuser(
            "g5-admin", "admin@example.com", "test-pass-123"
        )
        self.institution = Institution.objects.create(name="مؤسسة أصلية")
        self.reference = MasterVersion.objects.create(
            number=1,
            name="مرجع الحوكمة",
            status=MasterStatus.PUBLISHED,
        )
        self.root = StructureNode.objects.create(
            master_version=self.reference,
            title="المجال الأصلي",
            sort_order=1,
        )
        ChecklistItem.objects.create(
            node=self.root,
            title="بند أصلي",
            sort_order=1,
        )
        self.inspection = Inspection.objects.create(
            institution=self.institution,
            inspector=self.inspector,
            master_version=self.reference,
            reference_name_snapshot=self.reference.name,
            visit_date=date(2026, 9, 18),
        )
        materialize_inspection(self.inspection)
        self.snap_root = self.inspection.inspection_nodes.get(source_node=self.root)

    def login_inspector(self):
        self.client.login(username="g5-inspector", password="test-pass-123")

    def login_admin(self):
        self.client.login(username="g5-admin", password="test-pass-123")

    def test_visit_local_content_is_immediate_but_not_auto_proposed(self):
        self.login_inspector()
        response = self.client.post(
            reverse("local_item_add", args=[self.inspection.pk, self.snap_root.pk]),
            {"title": "بند ميداني", "guidance": "تحقق ميدانيًا"},
        )
        self.assertEqual(response.status_code, 302)
        local = self.snap_root.item_results.get(title_snapshot="بند ميداني")
        self.assertEqual(local.scope_origin, ScopeOrigin.LOCAL)
        self.assertFalse(
            Proposal.objects.filter(
                source_inspection=self.inspection,
                proposal_type=ProposalType.ITEM,
                source_local_id=local.id,
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

    def test_inspector_cannot_access_admin_governance_or_shared_builder(self):
        self.login_inspector()
        self.assertEqual(self.client.get(reverse("proposal_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("builder_home")).status_code, 403)

    def test_legacy_content_proposals_are_preserved_but_hidden_from_admin_inbox(self):
        legacy = Proposal.objects.create(
            proposal_type=ProposalType.ITEM,
            source_inspection=self.inspection,
            source_local_id=999,
            proposed_by=self.inspector,
            payload={"title": "اقتراح عنصر قديم"},
        )
        self.login_admin()
        listing = self.client.get(reverse("proposal_list"))
        self.assertEqual(listing.status_code, 200)
        self.assertNotContains(listing, "اقتراح عنصر قديم")
        self.assertEqual(
            self.client.get(reverse("proposal_detail", args=[legacy.pk])).status_code,
            404,
        )
        legacy.refresh_from_db()
        self.assertEqual(legacy.status, ProposalStatus.PENDING)

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
            master_version=self.reference,
            reference_name_snapshot=self.reference.name,
            visit_date=date(2026, 9, 19),
        )
        proposal = Proposal.objects.get(
            proposal_type=ProposalType.INSTITUTION,
            source_local_id=local.id,
        )
        reject_proposal(proposal, self.admin, "ليست مؤسسة مستقلة")
        local.refresh_from_db()
        old_visit.refresh_from_db()
        self.assertEqual(
            local.verification_status,
            InstitutionVerificationStatus.REJECTED,
        )
        self.assertFalse(local.active)
        self.assertEqual(old_visit.institution_id, local.id)

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
            master_version=self.reference,
            reference_name_snapshot=self.reference.name,
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
