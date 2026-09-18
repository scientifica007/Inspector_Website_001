from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    FieldType, Inspection, InspectionNode, Institution, MasterStatus, MasterVersion,
    Profile, Proposal, ProposalStatus, ProposalType, ResultStatus, Role,
    SpecificationDefinition, StructureNode,
)

User = get_user_model()

class Gate1SpikeTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user("inspector", password="test-pass-123")
        Profile.objects.create(user=self.inspector, role=Role.INSPECTOR)
        self.other = User.objects.create_user("other", password="test-pass-123")
        Profile.objects.create(user=self.other, role=Role.INSPECTOR)
        self.version = MasterVersion.objects.create(number=1, status=MasterStatus.PUBLISHED)
        self.institution = Institution.objects.create(name="مؤسسة تجريبية")

    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_inspector_sees_only_own_inspections(self):
        own = Inspection.objects.create(
            institution=self.institution, inspector=self.inspector,
            master_version=self.version, visit_date=date(2026, 9, 18)
        )
        Inspection.objects.create(
            institution=self.institution, inspector=self.other,
            master_version=self.version, visit_date=date(2026, 9, 17)
        )
        self.client.login(username="inspector", password="test-pass-123")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(list(response.context["inspections"]), [own])

    def test_recursive_structure(self):
        root = StructureNode.objects.create(master_version=self.version, title="المجال")
        child = StructureNode.objects.create(master_version=self.version, parent=root, title="تحت المجال")
        grandchild = StructureNode.objects.create(master_version=self.version, parent=child, title="مصلحة")
        self.assertEqual(grandchild.parent.parent, root)
        self.assertEqual(root.children.first(), child)

    def test_dynamic_specification_definition(self):
        node = StructureNode.objects.create(master_version=self.version, title="مديرية فرعية")
        spec = SpecificationDefinition.objects.create(
            node=node, title="عدد الموظفين", field_type=FieldType.NUMBER, required=True
        )
        self.assertEqual(spec.field_type, FieldType.NUMBER)
        self.assertTrue(spec.required)

    def test_snapshot_survives_master_edit(self):
        node = StructureNode.objects.create(master_version=self.version, title="العنوان الأصلي")
        inspection = Inspection.objects.create(
            institution=self.institution, inspector=self.inspector,
            master_version=self.version, visit_date=date(2026, 9, 18)
        )
        snap = InspectionNode.objects.create(
            inspection=inspection, source_node=node, title_snapshot=node.title
        )
        node.title = "عنوان معدل لاحقًا"
        node.save(update_fields=["title"])
        snap.refresh_from_db()
        self.assertEqual(snap.title_snapshot, "العنوان الأصلي")

    def test_not_applicable_is_valid_result_status(self):
        self.assertIn(ResultStatus.NOT_APPLICABLE, ResultStatus.values)

    def test_field_addition_can_become_pending_proposal(self):
        inspection = Inspection.objects.create(
            institution=self.institution, inspector=self.inspector,
            master_version=self.version, visit_date=date(2026, 9, 18)
        )
        proposal = Proposal.objects.create(
            proposal_type=ProposalType.ITEM,
            source_inspection=inspection,
            proposed_by=self.inspector,
            payload={"title": "بند أضيف من الميدان"},
        )
        self.assertEqual(proposal.status, ProposalStatus.PENDING)
