import json
from datetime import date
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from .exporting import build_inspection_export
from .models import (
    ChecklistItem,
    FieldType,
    Inspection,
    InspectionItemResult,
    InspectionStatus,
    Institution,
    MasterStatus,
    MasterVersion,
    Proposal,
    ProposalStatus,
    ProposalType,
    ReferenceVisibility,
    ScopeOrigin,
    SpecificationDefinition,
    StructureNode,
)
from .services import materialize_inspection

User = get_user_model()

class ExportTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user("export-inspector", password="test-pass-123")
        self.other = User.objects.create_user("export-other", password="test-pass-123")
        self.admin = User.objects.create_superuser("export-admin", "admin@example.com", "test-pass-123")
        self.institution = Institution.objects.create(
            name="مؤسسة تجريبية عربية",
            institution_type="CFPA",
            commune="تبسة",
        )
        self.master = MasterVersion.objects.create(
            number=1,
            name="مرجع التصدير",
            status=MasterStatus.PUBLISHED,
        )
        self.root = StructureNode.objects.create(
            master_version=self.master,
            title="المجال الأول",
            description="وصف المجال",
            sort_order=10,
        )
        self.child = StructureNode.objects.create(
            master_version=self.master,
            parent=self.root,
            title="تحت المجال",
            sort_order=20,
        )
        self.spec = SpecificationDefinition.objects.create(
            node=self.root,
            title="عدد الموظفين",
            field_type=FieldType.NUMBER,
            sort_order=10,
        )
        self.item = ChecklistItem.objects.create(
            node=self.root,
            title="مطابقة الوثائق",
            guidance="تحقق من الوثائق",
            sort_order=10,
        )
        self.inspection = Inspection.objects.create(
            institution=self.institution,
            inspector=self.inspector,
            master_version=self.master,
            source_reference=self.master,
            reference_name_snapshot=self.master.name,
            visit_date=date(2026, 9, 18),
            general_observations="معاينة عامة",
            general_recommendations="توصية عامة",
        )
        materialize_inspection(self.inspection)
        self.snap_root = self.inspection.inspection_nodes.get(source_node=self.root)
        spec_value = self.snap_root.specification_values.get(source_specification=self.spec)
        spec_value.value = 14
        spec_value.save(update_fields=["value"])
        result = self.snap_root.item_results.get(source_item=self.item)
        result.status = "OBSERVATION"
        result.observation = "ملاحظة ميدانية"
        result.save(update_fields=["status", "observation"])

    def test_export_is_deterministic_and_recursive(self):
        first = build_inspection_export(self.inspection)
        second = build_inspection_export(self.inspection)
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], "inspection-export-v3")
        payload = first["inspection"]
        self.assertEqual(payload["institution"]["name"], "مؤسسة تجريبية عربية")
        self.assertEqual(payload["inspector"]["username"], "export-inspector")
        self.assertEqual(payload["reference"]["id"], self.master.id)
        self.assertEqual(payload["reference"]["name"], "مرجع التصدير")
        self.assertEqual(payload["scope_mode"], "SELECTIVE")
        self.assertEqual(payload["nodes"][0]["title"], "المجال الأول")
        self.assertEqual(payload["nodes"][0]["children"][0]["title"], "تحت المجال")
        self.assertEqual(payload["nodes"][0]["specifications"][0]["value"], 14)
        self.assertEqual(
            payload["nodes"][0]["checklist_items"][0]["observation"],
            "ملاحظة ميدانية",
        )

    def test_master_edits_do_not_change_export_snapshot(self):
        self.root.title = "عنوان Master معدل"
        self.root.save(update_fields=["title"])
        self.spec.title = "مواصفة Master معدلة"
        self.spec.save(update_fields=["title"])
        self.item.title = "بند Master معدل"
        self.item.save(update_fields=["title"])

        payload = build_inspection_export(self.inspection)["inspection"]["nodes"][0]
        self.assertEqual(payload["title"], "المجال الأول")
        self.assertEqual(payload["specifications"][0]["title"], "عدد الموظفين")
        self.assertEqual(payload["checklist_items"][0]["title"], "مطابقة الوثائق")

    def test_local_addition_export_contains_proposal_trace(self):
        local = InspectionItemResult.objects.create(
            inspection_node=self.snap_root,
            title_snapshot="بند محلي",
            guidance_snapshot="توجيه محلي",
            scope_origin=ScopeOrigin.LOCAL,
            sort_order_snapshot=99,
        )
        proposal = Proposal.objects.create(
            proposal_type=ProposalType.ITEM,
            source_inspection=self.inspection,
            source_local_id=local.id,
            proposed_by=self.inspector,
            status=ProposalStatus.PENDING,
            payload={"title": "بند محلي"},
        )
        items = build_inspection_export(self.inspection)["inspection"]["nodes"][0]["checklist_items"]
        exported = next(item for item in items if item["title"] == "بند محلي")
        self.assertEqual(exported["scope"]["origin"], ScopeOrigin.LOCAL)
        self.assertEqual(exported["scope"]["state"], "ACTIVE")
        self.assertEqual(exported["proposal"]["proposal_id"], proposal.id)
        self.assertEqual(exported["proposal"]["status"], ProposalStatus.PENDING)

    def test_local_export_uses_latest_proposal_for_same_snapshot(self):
        local = InspectionItemResult.objects.create(
            inspection_node=self.snap_root,
            title_snapshot="بند متعدد الاقتراحات",
            guidance_snapshot="",
            scope_origin=ScopeOrigin.LOCAL,
            sort_order_snapshot=100,
        )
        first = Proposal.objects.create(
            proposal_type=ProposalType.ITEM,
            source_inspection=self.inspection,
            source_local_id=local.id,
            proposed_by=self.inspector,
            status=ProposalStatus.WITHDRAWN,
            payload={"title": "صياغة أولى"},
        )
        latest = Proposal.objects.create(
            proposal_type=ProposalType.ITEM,
            source_inspection=self.inspection,
            source_local_id=local.id,
            proposed_by=self.inspector,
            status=ProposalStatus.PENDING,
            payload={"title": "صياغة حالية"},
        )

        items = build_inspection_export(self.inspection)["inspection"]["nodes"][0]["checklist_items"]
        exported = next(
            item for item in items if item["title"] == "بند متعدد الاقتراحات"
        )

        self.assertNotEqual(first.id, latest.id)
        self.assertEqual(exported["proposal"]["proposal_id"], latest.id)
        self.assertEqual(exported["proposal"]["status"], ProposalStatus.PENDING)

    def test_owner_and_admin_can_download_but_other_inspector_cannot(self):
        self.client.login(username="export-inspector", password="test-pass-123")
        owner_response = self.client.get(reverse("inspection_export", args=[self.inspection.pk]))
        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(owner_response["Content-Type"], "application/json; charset=utf-8")
        self.assertIn("attachment;", owner_response["Content-Disposition"])
        decoded = json.loads(owner_response.content.decode("utf-8"))
        self.assertEqual(decoded["inspection"]["id"], self.inspection.id)

        self.client.logout()
        self.client.login(username="export-other", password="test-pass-123")
        self.assertEqual(
            self.client.get(reverse("inspection_export", args=[self.inspection.pk])).status_code,
            404,
        )

        self.client.logout()
        self.client.login(username="export-admin", password="test-pass-123")
        self.assertEqual(
            self.client.get(reverse("inspection_export", args=[self.inspection.pk])).status_code,
            200,
        )

    def test_export_works_for_draft_and_completed_visits(self):
        self.client.login(username="export-inspector", password="test-pass-123")
        draft_body = self.client.get(
            reverse("inspection_export", args=[self.inspection.pk])
        ).content
        self.inspection.status = InspectionStatus.COMPLETED
        self.inspection.save(update_fields=["status"])
        complete_body = self.client.get(
            reverse("inspection_export", args=[self.inspection.pk])
        ).content
        self.assertEqual(json.loads(draft_body)["inspection"]["status"], "DRAFT")
        self.assertEqual(json.loads(complete_body)["inspection"]["status"], "COMPLETED")

class DemoSeedTests(TestCase):
    @override_settings(DEBUG=True)
    def test_seed_demo_creates_fictitious_pilot_data(self):
        out = StringIO()
        call_command(
            "seed_demo",
            username="pilot-test",
            password="strong-test-password-123",
            stdout=out,
        )
        self.assertTrue(User.objects.filter(username="pilot-test").exists())
        self.assertEqual(
            MasterVersion.objects.filter(status=MasterStatus.PUBLISHED).count(),
            1,
        )
        inspection = Inspection.objects.get(inspector__username="pilot-test")
        self.assertGreater(inspection.inspection_nodes.count(), 0)
        self.assertIsNotNone(inspection.source_reference_id)
        self.assertEqual(
            inspection.master_version.visibility,
            ReferenceVisibility.SNAPSHOT,
        )
        self.assertIn("Password was accepted but is not echoed.", out.getvalue())

    @override_settings(DEBUG=True)
    def test_seed_demo_refuses_existing_project_data(self):
        Institution.objects.create(name="بيانات موجودة")
        with self.assertRaises(CommandError):
            call_command(
                "seed_demo",
                username="pilot-test",
                password="strong-test-password-123",
            )

    @override_settings(DEBUG=False)
    def test_seed_demo_is_disabled_when_debug_false(self):
        with self.assertRaises(CommandError):
            call_command(
                "seed_demo",
                username="pilot-test",
                password="strong-test-password-123",
            )
