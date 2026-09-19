from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    ChecklistItem,
    FieldType,
    Inspection,
    InspectionStatus,
    Institution,
    MasterStatus,
    MasterVersion,
    ResultStatus,
    SpecificationDefinition,
    StructureNode,
)
from .services import materialize_inspection

User = get_user_model()

class InspectorFieldWorkflowTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user("field-inspector", password="test-pass-123")
        self.other = User.objects.create_user("field-other", password="test-pass-123")
        self.admin = User.objects.create_superuser("field-admin", "admin@example.com", "test-pass-123")
        self.institution = Institution.objects.create(name="مؤسسة الاختبار")
        self.version = MasterVersion.objects.create(number=1, status=MasterStatus.PUBLISHED)

    def build_reference(self):
        root = StructureNode.objects.create(
            master_version=self.version,
            title="المديرية الفرعية للدراسات والتربصات",
            description="العقدة الأصلية",
            sort_order=1,
        )
        child = StructureNode.objects.create(
            master_version=self.version,
            parent=root,
            title="مصلحة الدراسات",
            sort_order=2,
        )
        specs = {}
        specs["short"] = SpecificationDefinition.objects.create(
            node=root, title="اسم المسؤول", field_type=FieldType.SHORT_TEXT, required=True, sort_order=1
        )
        specs["long"] = SpecificationDefinition.objects.create(
            node=root, title="الوصف", field_type=FieldType.LONG_TEXT, sort_order=2
        )
        specs["number"] = SpecificationDefinition.objects.create(
            node=root, title="عدد الموظفين", field_type=FieldType.NUMBER, sort_order=3
        )
        specs["date"] = SpecificationDefinition.objects.create(
            node=root, title="تاريخ التعيين", field_type=FieldType.DATE, sort_order=4
        )
        specs["boolean"] = SpecificationDefinition.objects.create(
            node=root, title="يوجد سجل", field_type=FieldType.BOOLEAN, sort_order=5
        )
        specs["single"] = SpecificationDefinition.objects.create(
            node=root,
            title="نوع التنظيم",
            field_type=FieldType.SINGLE_SELECT,
            options=["A", "B"],
            help_text="اختر نوعًا واحدًا",
            sort_order=6,
        )
        specs["multi"] = SpecificationDefinition.objects.create(
            node=root,
            title="المصالح المتوفرة",
            field_type=FieldType.MULTI_SELECT,
            options=["X", "Y", "Z"],
            sort_order=7,
        )
        item = ChecklistItem.objects.create(
            node=root,
            title="مطابقة برنامج العمل",
            guidance="قارن البرنامج بالوثائق المعتمدة",
            sort_order=1,
        )
        ChecklistItem.objects.create(
            node=child,
            title="توفر سجل النشاط",
            sort_order=1,
        )
        return root, child, specs, item

    def make_inspection(self, *, inspector=None):
        inspection = Inspection.objects.create(
            institution=self.institution,
            inspector=inspector or self.inspector,
            master_version=self.version,
            visit_date=date(2026, 9, 18),
        )
        materialize_inspection(inspection)
        return inspection

    def test_materialization_preserves_hierarchy_specs_items_and_metadata(self):
        root, child, specs, item = self.build_reference()
        inspection = self.make_inspection()
        nodes = list(inspection.inspection_nodes.order_by("sort_order_snapshot", "id"))
        self.assertEqual(len(nodes), 2)
        snap_root = inspection.inspection_nodes.get(source_node=root)
        snap_child = inspection.inspection_nodes.get(source_node=child)
        self.assertEqual(snap_child.parent, snap_root)

        single = snap_root.specification_values.get(source_specification=specs["single"])
        self.assertEqual(single.options_snapshot, ["A", "B"])
        self.assertEqual(single.help_text_snapshot, "اختر نوعًا واحدًا")
        self.assertFalse(single.required_snapshot)

        item_snap = snap_root.item_results.get(source_item=item)
        self.assertEqual(item_snap.guidance_snapshot, "قارن البرنامج بالوثائق المعتمدة")
        self.assertEqual(item_snap.status, ResultStatus.UNCHECKED)

    def test_snapshot_is_stable_after_master_edits(self):
        root, _, specs, item = self.build_reference()
        inspection = self.make_inspection()
        snap_root = inspection.inspection_nodes.get(source_node=root)
        spec_snap = snap_root.specification_values.get(source_specification=specs["single"])
        item_snap = snap_root.item_results.get(source_item=item)

        root.title = "عنوان جديد"
        root.save(update_fields=["title"])
        specs["single"].title = "مواصفة جديدة"
        specs["single"].options = ["C"]
        specs["single"].help_text = "شرح جديد"
        specs["single"].save(update_fields=["title", "options", "help_text"])
        item.title = "بند جديد"
        item.guidance = "توجيه جديد"
        item.save(update_fields=["title", "guidance"])

        snap_root.refresh_from_db()
        spec_snap.refresh_from_db()
        item_snap.refresh_from_db()
        self.assertEqual(snap_root.title_snapshot, "المديرية الفرعية للدراسات والتربصات")
        self.assertEqual(spec_snap.title_snapshot, "نوع التنظيم")
        self.assertEqual(spec_snap.options_snapshot, ["A", "B"])
        self.assertEqual(spec_snap.help_text_snapshot, "اختر نوعًا واحدًا")
        self.assertEqual(item_snap.title_snapshot, "مطابقة برنامج العمل")
        self.assertEqual(item_snap.guidance_snapshot, "قارن البرنامج بالوثائق المعتمدة")

    def test_inactive_parent_hides_whole_branch_from_materialization(self):
        hidden = StructureNode.objects.create(
            master_version=self.version, title="مخفي", active=False
        )
        StructureNode.objects.create(
            master_version=self.version, parent=hidden, title="ابن نشط", active=True
        )
        visible = StructureNode.objects.create(
            master_version=self.version, title="ظاهر", active=True
        )
        inspection = self.make_inspection()
        titles = list(inspection.inspection_nodes.values_list("title_snapshot", flat=True))
        self.assertEqual(titles, [visible.title])

    def test_inspection_creation_view_starts_with_empty_selective_scope(self):
        self.build_reference()
        self.client.login(username="field-inspector", password="test-pass-123")
        response = self.client.post(
            reverse("inspection_create"),
            {"institution": self.institution.id, "visit_date": "2026-09-18"},
        )
        inspection = Inspection.objects.get(inspector=self.inspector)
        self.assertRedirects(response, reverse("inspection_detail", args=[inspection.pk]))
        self.assertEqual(inspection.scope_mode, "SELECTIVE")
        self.assertFalse(inspection.inspection_nodes.exists())

    def test_other_inspector_cannot_open_visit_or_node(self):
        root, _, _, _ = self.build_reference()
        inspection = self.make_inspection()
        node = inspection.inspection_nodes.get(source_node=root)
        self.client.login(username="field-other", password="test-pass-123")
        self.assertEqual(
            self.client.get(reverse("inspection_detail", args=[inspection.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("inspection_node", args=[inspection.pk, node.pk])
            ).status_code,
            404,
        )

    def test_admin_can_view_but_not_edit_an_inspectors_node(self):
        root, _, _, _ = self.build_reference()
        inspection = self.make_inspection()
        node = inspection.inspection_nodes.get(source_node=root)
        self.client.login(username="field-admin", password="test-pass-123")
        self.assertEqual(
            self.client.get(reverse("inspection_detail", args=[inspection.pk])).status_code,
            200,
        )
        response = self.client.post(
            reverse("inspection_node", args=[inspection.pk, node.pk]),
            {"additional_observations": "محاولة تعديل"},
        )
        self.assertEqual(response.status_code, 403)

    def test_all_dynamic_field_types_and_item_result_persist(self):
        root, _, specs, item = self.build_reference()
        inspection = self.make_inspection()
        node = inspection.inspection_nodes.get(source_node=root)
        values = {
            x.source_specification_id: x
            for x in node.specification_values.all()
        }
        item_result = node.item_results.get(source_item=item)

        data = {
            f"spec_{values[specs['short'].id].id}": "مسؤول تجريبي",
            f"spec_{values[specs['long'].id].id}": "وصف طويل",
            f"spec_{values[specs['number'].id].id}": "12.5",
            f"spec_{values[specs['date'].id].id}": "2026-09-18",
            f"spec_{values[specs['boolean'].id].id}": "false",
            f"spec_{values[specs['single'].id].id}": "B",
            f"spec_{values[specs['multi'].id].id}": ["X", "Z"],
            f"status_{item_result.id}": ResultStatus.NON_COMPLIANT,
            f"observation_{item_result.id}": "يوجد فرق بين البرنامج والتنفيذ",
            "additional_observations": "معاينة إضافية",
            "recommendations": "تحيين البرنامج",
        }

        self.client.login(username="field-inspector", password="test-pass-123")
        response = self.client.post(
            reverse("inspection_node", args=[inspection.pk, node.pk]),
            data,
        )
        self.assertRedirects(
            response, reverse("inspection_node", args=[inspection.pk, node.pk])
        )

        for value in values.values():
            value.refresh_from_db()
        self.assertEqual(values[specs["short"].id].value, "مسؤول تجريبي")
        self.assertEqual(values[specs["long"].id].value, "وصف طويل")
        self.assertEqual(values[specs["number"].id].value, 12.5)
        self.assertEqual(values[specs["date"].id].value, "2026-09-18")
        self.assertIs(values[specs["boolean"].id].value, False)
        self.assertEqual(values[specs["single"].id].value, "B")
        self.assertEqual(values[specs["multi"].id].value, ["X", "Z"])

        item_result.refresh_from_db()
        node.refresh_from_db()
        self.assertEqual(item_result.status, ResultStatus.NON_COMPLIANT)
        self.assertEqual(item_result.observation, "يوجد فرق بين البرنامج والتنفيذ")
        self.assertEqual(node.additional_observations, "معاينة إضافية")
        self.assertEqual(node.recommendations, "تحيين البرنامج")

    def test_invalid_item_status_does_not_mutate_result(self):
        root, _, _, item = self.build_reference()
        inspection = self.make_inspection()
        node = inspection.inspection_nodes.get(source_node=root)
        result = node.item_results.get(source_item=item)
        self.client.login(username="field-inspector", password="test-pass-123")
        response = self.client.post(
            reverse("inspection_node", args=[inspection.pk, node.pk]),
            {
                f"status_{result.id}": "INVALID",
                f"observation_{result.id}": "لا تحفظ",
                "additional_observations": "",
                "recommendations": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        result.refresh_from_db()
        self.assertEqual(result.status, ResultStatus.UNCHECKED)
        self.assertEqual(result.observation, "")

    def test_general_observations_and_recommendations_persist(self):
        self.build_reference()
        inspection = self.make_inspection()
        self.client.login(username="field-inspector", password="test-pass-123")
        response = self.client.post(
            reverse("inspection_general", args=[inspection.pk]),
            {
                "general_observations": "معاينة عامة",
                "general_recommendations": "توصية عامة",
            },
        )
        self.assertRedirects(response, reverse("inspection_detail", args=[inspection.pk]))
        inspection.refresh_from_db()
        self.assertEqual(inspection.general_observations, "معاينة عامة")
        self.assertEqual(inspection.general_recommendations, "توصية عامة")

    def test_completion_requires_confirmation_and_locks_editing(self):
        root, _, _, _ = self.build_reference()
        inspection = self.make_inspection()
        node = inspection.inspection_nodes.get(source_node=root)
        self.client.login(username="field-inspector", password="test-pass-123")

        response = self.client.post(reverse("inspection_complete", args=[inspection.pk]), {})
        self.assertEqual(response.status_code, 200)
        inspection.refresh_from_db()
        self.assertEqual(inspection.status, InspectionStatus.DRAFT)

        response = self.client.post(
            reverse("inspection_complete", args=[inspection.pk]),
            {"confirm": "on"},
        )
        self.assertRedirects(response, reverse("inspection_detail", args=[inspection.pk]))
        inspection.refresh_from_db()
        self.assertEqual(inspection.status, InspectionStatus.COMPLETED)

        response = self.client.post(
            reverse("inspection_node", args=[inspection.pk, node.pk]),
            {"additional_observations": "بعد الإغلاق"},
        )
        self.assertEqual(response.status_code, 409)
        node.refresh_from_db()
        self.assertNotEqual(node.additional_observations, "بعد الإغلاق")
