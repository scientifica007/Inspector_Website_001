from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    FieldType,
    Inspection,
    InspectionNode,
    Institution,
    InstitutionVerificationStatus,
    MasterStatus,
    MasterVersion,
    Profile,
    Proposal,
    ProposalStatus,
    ProposalType,
    ReferenceVisibility,
    ResultStatus,
    Role,
    SpecificationDefinition,
    SpecificationValue,
    StructureNode,
)

User = get_user_model()

class Gate2CoreTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user("inspector", password="test-pass-123")
        self.other = User.objects.create_user("other", password="test-pass-123")
        self.published = MasterVersion.objects.create(
            number=1,
            name="مرجع أساسي",
            status=MasterStatus.PUBLISHED,
        )
        self.institution = Institution.objects.create(
            name="مؤسسة معتمدة",
            verification_status=InstitutionVerificationStatus.VERIFIED,
        )

    def test_profile_is_created_automatically(self):
        self.assertEqual(self.inspector.profile.role, Role.INSPECTOR)

    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_inspector_sees_only_own_inspections(self):
        own = Inspection.objects.create(
            institution=self.institution,
            inspector=self.inspector,
            master_version=self.published,
            visit_date=date(2026, 9, 18),
        )
        Inspection.objects.create(
            institution=self.institution,
            inspector=self.other,
            master_version=self.published,
            visit_date=date(2026, 9, 17),
        )
        self.client.login(username="inspector", password="test-pass-123")
        response = self.client.get(reverse("inspection_list"))
        self.assertEqual(list(response.context["inspections"]), [own])

    def test_admin_sees_all_inspections(self):
        admin = User.objects.create_superuser("admin", "admin@example.com", "test-pass-123")
        self.assertEqual(admin.profile.role, Role.ADMIN)
        Inspection.objects.create(
            institution=self.institution,
            inspector=self.inspector,
            master_version=self.published,
            visit_date=date(2026, 9, 18),
        )
        Inspection.objects.create(
            institution=self.institution,
            inspector=self.other,
            master_version=self.published,
            visit_date=date(2026, 9, 17),
        )
        self.client.login(username="admin", password="test-pass-123")
        response = self.client.get(reverse("inspection_list"))
        self.assertEqual(response.context["inspections"].count(), 2)

    def test_inspector_added_institution_is_pending_and_proposed(self):
        self.client.login(username="inspector", password="test-pass-123")
        response = self.client.post(
            reverse("institution_create"),
            {"name": "مؤسسة ميدانية", "institution_type": "CFPA", "commune": "تبسة"},
        )
        self.assertRedirects(response, reverse("institution_list"))
        institution = Institution.objects.get(name="مؤسسة ميدانية")
        self.assertEqual(institution.created_by, self.inspector)
        self.assertEqual(
            institution.verification_status,
            InstitutionVerificationStatus.PENDING,
        )
        proposal = Proposal.objects.get(proposal_type=ProposalType.INSTITUTION)
        self.assertEqual(proposal.status, ProposalStatus.PENDING)
        self.assertEqual(proposal.payload["institution_id"], institution.id)

    def test_pending_institution_is_not_visible_to_other_inspector(self):
        Institution.objects.create(
            name="مؤسسة خاصة مؤقتًا",
            created_by=self.inspector,
            verification_status=InstitutionVerificationStatus.PENDING,
        )
        self.client.login(username="other", password="test-pass-123")
        response = self.client.get(reverse("institution_list"))
        self.assertNotContains(response, "مؤسسة خاصة مؤقتًا")

    def test_pending_institution_is_visible_to_creator(self):
        Institution.objects.create(
            name="مؤسسة خاصة مؤقتًا",
            created_by=self.inspector,
            verification_status=InstitutionVerificationStatus.PENDING,
        )
        self.client.login(username="inspector", password="test-pass-123")
        response = self.client.get(reverse("institution_list"))
        self.assertContains(response, "مؤسسة خاصة مؤقتًا")

    def test_duplicate_institution_name_is_rejected_case_insensitively(self):
        Institution.objects.create(name="CFPA TEBESSA")
        self.client.login(username="inspector", password="test-pass-123")
        response = self.client.post(
            reverse("institution_create"),
            {"name": "cfpa tebessa", "institution_type": "", "commune": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "هذه المؤسسة موجودة مسبقًا")

    def test_new_inspection_uses_explicitly_selected_reference(self):
        second = MasterVersion.objects.create(
            number=2,
            name="مرجع ثان",
            status=MasterStatus.PUBLISHED,
        )
        self.client.login(username="inspector", password="test-pass-123")
        response = self.client.post(
            reverse("inspection_create"),
            {
                "institution": self.institution.id,
                "visit_date": "2026-09-18",
                "reference": second.id,
            },
        )
        inspection = Inspection.objects.get(inspector=self.inspector)
        self.assertRedirects(
            response,
            reverse("inspection_detail", args=[inspection.pk]),
        )
        self.assertEqual(inspection.source_reference, second)
        self.assertNotEqual(inspection.master_version_id, second.id)
        self.assertEqual(
            inspection.master_version.visibility,
            ReferenceVisibility.SNAPSHOT,
        )
        self.assertEqual(inspection.reference_name_snapshot, "مرجع ثان")
        self.assertEqual(inspection.status, "DRAFT")

    def test_new_inspection_can_start_without_reference(self):
        self.client.login(username="inspector", password="test-pass-123")
        response = self.client.post(
            reverse("inspection_create"),
            {
                "institution": self.institution.id,
                "visit_date": "2026-09-18",
                "reference": "",
            },
        )
        inspection = Inspection.objects.get(inspector=self.inspector)
        self.assertRedirects(
            response,
            reverse("inspection_detail", args=[inspection.pk]),
        )
        self.assertIsNone(inspection.master_version_id)
        self.assertIsNone(inspection.source_reference_id)
        self.assertEqual(inspection.reference_name_snapshot, "")

    def test_recursive_structure(self):
        root = StructureNode.objects.create(master_version=self.published, title="المجال")
        child = StructureNode.objects.create(
            master_version=self.published, parent=root, title="تحت المجال"
        )
        grandchild = StructureNode.objects.create(
            master_version=self.published, parent=child, title="مصلحة"
        )
        self.assertEqual(grandchild.parent.parent, root)

    def test_dynamic_specification_value_keeps_snapshot(self):
        node = StructureNode.objects.create(
            master_version=self.published, title="مديرية فرعية"
        )
        spec = SpecificationDefinition.objects.create(
            node=node,
            title="عدد الموظفين",
            field_type=FieldType.NUMBER,
            required=True,
        )
        inspection = Inspection.objects.create(
            institution=self.institution,
            inspector=self.inspector,
            master_version=self.published,
            visit_date=date(2026, 9, 18),
        )
        inspection_node = InspectionNode.objects.create(
            inspection=inspection,
            source_node=node,
            title_snapshot=node.title,
        )
        value = SpecificationValue.objects.create(
            inspection_node=inspection_node,
            source_specification=spec,
            title_snapshot=spec.title,
            field_type_snapshot=spec.field_type,
            value=14,
        )
        spec.title = "عدد العمال"
        spec.save(update_fields=["title"])
        value.refresh_from_db()
        self.assertEqual(value.title_snapshot, "عدد الموظفين")
        self.assertEqual(value.value, 14)

    def test_not_applicable_is_a_standard_result_status(self):
        self.assertIn(ResultStatus.NOT_APPLICABLE, ResultStatus.values)
