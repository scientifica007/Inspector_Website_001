from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .builder_forms import SpecificationDefinitionForm, StructureNodeForm
from .models import (
    ChecklistItem,
    FieldType,
    Inspection,
    InspectionNode,
    Institution,
    MasterStatus,
    MasterVersion,
    ReferenceVisibility,
    SpecificationDefinition,
    StructureNode,
)
from .services import flatten_nodes

User = get_user_model()


class AdminBuilderTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            "admin-builder", "admin@example.com", "test-pass-123"
        )
        self.inspector = User.objects.create_user(
            "inspector-builder", password="test-pass-123"
        )
        self.institution = Institution.objects.create(name="مؤسسة مرجعية")

    def login_admin(self):
        self.client.login(username="admin-builder", password="test-pass-123")

    def make_reference(self, number, name):
        return MasterVersion.objects.create(
            number=number,
            name=name,
            visibility=ReferenceVisibility.SHARED,
            status=MasterStatus.PUBLISHED,
        )

    def test_builder_is_admin_only(self):
        self.client.login(username="inspector-builder", password="test-pass-123")
        self.assertEqual(self.client.get(reverse("builder_home")).status_code, 403)

    def test_admin_builder_is_reference_library(self):
        first = self.make_reference(1, "مرجع بيداغوجي")
        second = self.make_reference(2, "مرجع التجهيزات")
        self.login_admin()
        response = self.client.get(reverse("builder_home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "مراجع التفتيش")
        self.assertContains(response, first.name)
        self.assertContains(response, second.name)
        self.assertNotContains(response, "المسودة الحالية")

    def test_admin_can_create_multiple_shared_references_without_superseding(self):
        self.login_admin()
        for name in ("مرجع أول", "مرجع ثان"):
            response = self.client.post(
                reverse("builder_reference_create"),
                {"name": name},
            )
            reference = MasterVersion.objects.get(name=name)
            self.assertRedirects(
                response,
                reverse("builder_reference", args=[reference.pk]),
            )
            self.assertEqual(reference.visibility, ReferenceVisibility.SHARED)

        self.assertEqual(
            MasterVersion.objects.filter(visibility=ReferenceVisibility.SHARED).count(),
            2,
        )
        self.assertTrue(MasterVersion.objects.filter(name="مرجع أول").exists())
        self.assertTrue(MasterVersion.objects.filter(name="مرجع ثان").exists())

    def test_node_form_blocks_cross_reference_parent(self):
        reference = self.make_reference(1, "المرجع أ")
        other = self.make_reference(2, "المرجع ب")
        foreign_parent = StructureNode.objects.create(
            master_version=other,
            title="خارج المرجع",
        )
        form = StructureNodeForm(
            data={
                "title": "عنصر",
                "description": "",
                "inspectable": "on",
                "parent": foreign_parent.pk,
                "sort_order": 0,
                "active": "on",
            },
            reference=reference,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("parent", form.errors)

    def test_node_form_blocks_recursive_cycle(self):
        reference = self.make_reference(1, "مرجع")
        root = StructureNode.objects.create(master_version=reference, title="جذر")
        child = StructureNode.objects.create(
            master_version=reference,
            parent=root,
            title="فرع",
        )
        form = StructureNodeForm(
            data={
                "title": root.title,
                "description": "",
                "inspectable": "on",
                "parent": child.pk,
                "sort_order": 0,
                "active": "on",
            },
            instance=root,
            reference=reference,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("parent", form.errors)

    def test_admin_can_create_child_node_in_selected_reference(self):
        reference = self.make_reference(1, "مرجع التنظيم")
        parent = StructureNode.objects.create(
            master_version=reference,
            title="مديرية فرعية",
        )
        self.login_admin()
        response = self.client.post(
            reverse("builder_node_create", args=[reference.pk]),
            {
                "title": "مصلحة الدراسات",
                "description": "",
                "inspectable": "on",
                "parent": parent.pk,
                "sort_order": 1,
                "active": "on",
            },
        )
        child = StructureNode.objects.get(title="مصلحة الدراسات")
        self.assertRedirects(response, reverse("builder_node", args=[child.pk]))
        self.assertEqual(child.parent, parent)
        self.assertEqual(child.master_version, reference)

    def test_select_description_requires_options_and_parses_lines(self):
        reference = self.make_reference(1, "مرجع")
        node = StructureNode.objects.create(master_version=reference, title="مجال")
        invalid = SpecificationDefinitionForm(
            data={
                "title": "نوع المقر",
                "field_type": FieldType.SINGLE_SELECT,
                "required": "",
                "help_text": "",
                "sort_order": 0,
                "active": "on",
                "options_text": "",
            },
            node=node,
        )
        self.assertFalse(invalid.is_valid())

        valid = SpecificationDefinitionForm(
            data={
                "title": "نوع المقر",
                "field_type": FieldType.SINGLE_SELECT,
                "required": "",
                "help_text": "",
                "sort_order": 0,
                "active": "on",
                "options_text": "ملكية\nإيجار\nملحقة",
            },
            node=node,
        )
        self.assertTrue(valid.is_valid(), valid.errors)
        spec = valid.save()
        self.assertEqual(spec.options, ["ملكية", "إيجار", "ملحقة"])

    def test_any_admin_reference_can_be_edited_directly(self):
        reference = self.make_reference(1, "مرجع مشترك")
        node = StructureNode.objects.create(
            master_version=reference,
            title="قبل التعديل",
        )
        self.login_admin()
        response = self.client.post(
            reverse("builder_node_edit", args=[node.pk]),
            {
                "title": "بعد التعديل",
                "description": "",
                "inspectable": "on",
                "parent": "",
                "sort_order": 0,
                "active": "on",
            },
        )
        self.assertRedirects(response, reverse("builder_node", args=[node.pk]))
        node.refresh_from_db()
        self.assertEqual(node.title, "بعد التعديل")

    def test_admin_can_hard_delete_reference_content_without_deleting_visit_snapshot(self):
        reference = self.make_reference(1, "مرجع قابل للحذف")
        node = StructureNode.objects.create(
            master_version=reference,
            title="عنصر مصدر",
        )
        inspection = Inspection.objects.create(
            institution=self.institution,
            inspector=self.inspector,
            master_version=reference,
            reference_name_snapshot=reference.name,
            visit_date=date(2026, 9, 19),
        )
        snapshot = InspectionNode.objects.create(
            inspection=inspection,
            source_node=node,
            title_snapshot="عنصر مصدر",
        )

        self.login_admin()
        self.client.post(reverse("builder_node_delete", args=[node.pk]))

        snapshot.refresh_from_db()
        self.assertIsNone(snapshot.source_node_id)
        self.assertEqual(snapshot.title_snapshot, "عنصر مصدر")
        self.assertTrue(Inspection.objects.filter(pk=inspection.pk).exists())

    def test_admin_can_delete_reference_without_deleting_inspection(self):
        reference = self.make_reference(1, "مرجع سيحذف")
        inspection = Inspection.objects.create(
            institution=self.institution,
            inspector=self.inspector,
            master_version=reference,
            reference_name_snapshot=reference.name,
            visit_date=date(2026, 9, 19),
        )

        self.login_admin()
        response = self.client.post(
            reverse("builder_reference_delete", args=[reference.pk])
        )
        self.assertRedirects(response, reverse("builder_home"))

        inspection.refresh_from_db()
        self.assertIsNone(inspection.master_version_id)
        self.assertEqual(inspection.reference_name_snapshot, "مرجع سيحذف")

    def test_inactive_branch_is_hidden_from_preview_tree(self):
        reference = self.make_reference(1, "مرجع")
        hidden = StructureNode.objects.create(
            master_version=reference,
            title="فرع معطل",
            active=False,
        )
        StructureNode.objects.create(
            master_version=reference,
            parent=hidden,
            title="ابن نشط",
            active=True,
        )
        StructureNode.objects.create(
            master_version=reference,
            title="فرع ظاهر",
            active=True,
        )
        titles = [node.title for node, _ in flatten_nodes(reference, active_only=True)]
        self.assertEqual(titles, ["فرع ظاهر"])
