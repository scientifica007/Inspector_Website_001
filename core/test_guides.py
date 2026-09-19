from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .guides import apply_guide
from .models import (
    ChecklistItem,
    FieldType,
    Guide,
    GuideApplication,
    GuideEntry,
    GuideEntryType,
    Inspection,
    InspectionItemResult,
    InspectionStatus,
    Institution,
    MasterStatus,
    MasterVersion,
    ReferenceVisibility,
    ScopeOrigin,
    ScopeRole,
    ScopeState,
    SpecificationDefinition,
    SpecificationValue,
    StructureNode,
)
from .reference_library import freeze_reference_for_inspection
from .services import add_scope_item, exclude_scope_item

User = get_user_model()


class GuideCoreTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user(
            "guide-inspector", password="test-pass-123"
        )
        self.other = User.objects.create_user(
            "guide-other", password="test-pass-123"
        )
        self.admin = User.objects.create_superuser(
            "guide-admin", "admin@example.com", "test-pass-123"
        )
        self.institution = Institution.objects.create(name="مؤسسة الأدلة")
        self.source = MasterVersion.objects.create(
            number=1,
            name="مرجع الأدلة",
            visibility=ReferenceVisibility.SHARED,
            status=MasterStatus.PUBLISHED,
        )
        self.root = StructureNode.objects.create(
            master_version=self.source,
            title="الإدارة",
            sort_order=10,
        )
        self.child = StructureNode.objects.create(
            master_version=self.source,
            parent=self.root,
            title="المصلحة",
            sort_order=10,
        )
        self.other_root = StructureNode.objects.create(
            master_version=self.source,
            title="الورشات",
            sort_order=20,
        )
        self.root_spec = SpecificationDefinition.objects.create(
            node=self.root,
            title="اسم المسؤول",
            field_type=FieldType.SHORT_TEXT,
            sort_order=10,
        )
        self.child_spec = SpecificationDefinition.objects.create(
            node=self.child,
            title="عدد الموظفين",
            field_type=FieldType.NUMBER,
            sort_order=10,
        )
        self.root_item = ChecklistItem.objects.create(
            node=self.root,
            title="بند الجذر",
            sort_order=10,
        )
        self.child_item = ChecklistItem.objects.create(
            node=self.child,
            title="بند المصلحة",
            sort_order=10,
        )
        self.other_item = ChecklistItem.objects.create(
            node=self.other_root,
            title="بند الورشات",
            sort_order=10,
        )
        self.inspection = self._new_inspection()
        self.guide = Guide.objects.create(
            reference=self.source,
            name="دليل الزيارة البيداغوجية",
            description="اقتراح اختياري",
            created_by=self.admin,
        )

    def _new_inspection(self):
        frozen = freeze_reference_for_inspection(self.source)
        return Inspection.objects.create(
            institution=self.institution,
            inspector=self.inspector,
            master_version=frozen,
            source_reference=self.source,
            reference_name_snapshot=self.source.name,
            visit_date=date(2026, 9, 19),
        )

    def _entry(self, entry_type, source_obj, order=10):
        return GuideEntry.objects.create(
            guide=self.guide,
            entry_type=entry_type,
            stable_id=source_obj.stable_id,
            label_snapshot=source_obj.title,
            sort_order=order,
        )

    def _frozen_item(self, source_item):
        return ChecklistItem.objects.get(
            node__master_version=self.inspection.master_version,
            stable_id=source_item.stable_id,
        )

    def test_single_item_guide_adds_only_context_path_and_guide_item(self):
        self._entry(GuideEntryType.ITEM, self.child_item)

        application, created = apply_guide(
            self.inspection, self.guide, self.inspector
        )

        self.assertTrue(created)
        self.assertEqual(application.applied_count, 1)
        self.assertEqual(application.skipped_count, 0)
        self.assertEqual(self.inspection.inspection_nodes.count(), 2)

        root_snapshot = self.inspection.inspection_nodes.get(
            source_node__stable_id=self.root.stable_id
        )
        child_snapshot = self.inspection.inspection_nodes.get(
            source_node__stable_id=self.child.stable_id
        )
        result = child_snapshot.item_results.get(
            source_item__stable_id=self.child_item.stable_id
        )
        self.assertEqual(root_snapshot.scope_role, ScopeRole.CONTEXT)
        self.assertEqual(child_snapshot.scope_role, ScopeRole.CONTEXT)
        self.assertEqual(root_snapshot.scope_origin, ScopeOrigin.GUIDE)
        self.assertEqual(child_snapshot.scope_origin, ScopeOrigin.GUIDE)
        self.assertEqual(result.scope_origin, ScopeOrigin.GUIDE)
        self.assertFalse(result.scope_locked)
        self.assertFalse(result.completion_required)
        self.assertFalse(root_snapshot.item_results.exists())
        self.assertFalse(
            self.inspection.inspection_nodes.filter(
                source_node__stable_id=self.other_root.stable_id
            ).exists()
        )

    def test_single_description_guide_adds_no_unrelated_item(self):
        self._entry(GuideEntryType.SPECIFICATION, self.child_spec)

        apply_guide(self.inspection, self.guide, self.inspector)

        child_snapshot = self.inspection.inspection_nodes.get(
            source_node__stable_id=self.child.stable_id
        )
        value = child_snapshot.specification_values.get(
            source_specification__stable_id=self.child_spec.stable_id
        )
        self.assertEqual(value.scope_origin, ScopeOrigin.GUIDE)
        self.assertFalse(value.scope_locked)
        self.assertFalse(value.completion_required)
        self.assertFalse(child_snapshot.item_results.exists())

    def test_branch_guide_is_recursive_optional_and_does_not_pull_sibling_root(self):
        self._entry(GuideEntryType.BRANCH, self.root)

        apply_guide(self.inspection, self.guide, self.inspector)

        root_snapshot = self.inspection.inspection_nodes.get(
            source_node__stable_id=self.root.stable_id
        )
        child_snapshot = self.inspection.inspection_nodes.get(
            source_node__stable_id=self.child.stable_id
        )
        self.assertEqual(root_snapshot.scope_role, ScopeRole.SELECTED)
        self.assertEqual(child_snapshot.scope_role, ScopeRole.SELECTED)
        self.assertEqual(root_snapshot.scope_origin, ScopeOrigin.GUIDE)
        self.assertEqual(child_snapshot.scope_origin, ScopeOrigin.GUIDE)
        self.assertTrue(root_snapshot.specification_values.exists())
        self.assertTrue(root_snapshot.item_results.exists())
        self.assertTrue(child_snapshot.specification_values.exists())
        self.assertTrue(child_snapshot.item_results.exists())
        self.assertFalse(root_snapshot.scope_locked)
        self.assertFalse(child_snapshot.scope_locked)
        self.assertFalse(
            SpecificationValue.objects.filter(
                inspection_node__inspection=self.inspection,
                completion_required=True,
            ).exists()
        )
        self.assertFalse(
            InspectionItemResult.objects.filter(
                inspection_node__inspection=self.inspection,
                completion_required=True,
            ).exists()
        )
        self.assertFalse(
            self.inspection.inspection_nodes.filter(
                source_node__stable_id=self.other_root.stable_id
            ).exists()
        )

    def test_existing_manual_item_keeps_manual_origin_when_guide_overlaps(self):
        frozen_item = self._frozen_item(self.child_item)
        manual = add_scope_item(
            self.inspection,
            frozen_item,
            origin=ScopeOrigin.MANUAL,
        )
        original_id = manual.id
        self._entry(GuideEntryType.ITEM, self.child_item)

        application, _ = apply_guide(
            self.inspection, self.guide, self.inspector
        )

        manual.refresh_from_db()
        self.assertEqual(manual.id, original_id)
        self.assertEqual(manual.scope_origin, ScopeOrigin.MANUAL)
        self.assertEqual(
            application.result_details[0]["status"],
            "already_present",
        )
        self.assertEqual(
            InspectionItemResult.objects.filter(
                inspection_node__inspection=self.inspection,
                source_item__stable_id=self.child_item.stable_id,
            ).count(),
            1,
        )

    def test_excluded_manual_item_is_reactivated_without_origin_rewrite(self):
        frozen_item = self._frozen_item(self.child_item)
        manual = add_scope_item(
            self.inspection,
            frozen_item,
            origin=ScopeOrigin.MANUAL,
        )
        exclude_scope_item(manual)
        manual.refresh_from_db()
        self.assertEqual(manual.scope_state, ScopeState.EXCLUDED)

        self._entry(GuideEntryType.ITEM, self.child_item)
        apply_guide(self.inspection, self.guide, self.inspector)

        manual.refresh_from_db()
        self.assertEqual(manual.scope_state, ScopeState.ACTIVE)
        self.assertEqual(manual.scope_origin, ScopeOrigin.MANUAL)

    def test_applying_same_guide_twice_is_idempotent(self):
        self._entry(GuideEntryType.ITEM, self.child_item)
        first, created = apply_guide(
            self.inspection, self.guide, self.inspector
        )
        count_after_first = InspectionItemResult.objects.filter(
            inspection_node__inspection=self.inspection
        ).count()

        second, created_again = apply_guide(
            self.inspection, self.guide, self.inspector
        )

        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            InspectionItemResult.objects.filter(
                inspection_node__inspection=self.inspection
            ).count(),
            count_after_first,
        )
        self.assertEqual(
            GuideApplication.objects.filter(
                inspection=self.inspection,
                guide=self.guide,
            ).count(),
            1,
        )

    def test_guide_entry_newer_than_frozen_draft_is_skipped_explicitly(self):
        new_item = ChecklistItem.objects.create(
            node=self.child,
            title="بند أضيف بعد إنشاء المسودة",
            sort_order=30,
        )
        self._entry(GuideEntryType.ITEM, new_item)

        application, _ = apply_guide(
            self.inspection, self.guide, self.inspector
        )

        self.assertEqual(application.applied_count, 0)
        self.assertEqual(application.skipped_count, 1)
        self.assertEqual(application.result_details[0]["status"], "missing")
        self.assertFalse(
            InspectionItemResult.objects.filter(
                inspection_node__inspection=self.inspection,
                title_snapshot=new_item.title,
            ).exists()
        )

    def test_guide_created_before_new_draft_resolves_by_stable_id(self):
        self._entry(GuideEntryType.ITEM, self.child_item)
        newer_inspection = self._new_inspection()

        application, _ = apply_guide(
            newer_inspection, self.guide, self.inspector
        )

        self.assertEqual(application.applied_count, 1)
        self.assertEqual(application.skipped_count, 0)
        self.assertTrue(
            InspectionItemResult.objects.filter(
                inspection_node__inspection=newer_inspection,
                source_item__stable_id=self.child_item.stable_id,
                scope_origin=ScopeOrigin.GUIDE,
            ).exists()
        )

    def test_edit_or_delete_guide_after_application_does_not_rewrite_visit(self):
        self._entry(GuideEntryType.ITEM, self.child_item)
        application, _ = apply_guide(
            self.inspection, self.guide, self.inspector
        )
        result = InspectionItemResult.objects.get(
            inspection_node__inspection=self.inspection,
            source_item__stable_id=self.child_item.stable_id,
        )
        result_id = result.id

        self.guide.name = "اسم معدل بعد التطبيق"
        self.guide.save(update_fields=["name"])
        application.refresh_from_db()
        self.assertEqual(
            application.guide_name_snapshot,
            "دليل الزيارة البيداغوجية",
        )

        self.guide.delete()
        application.refresh_from_db()
        self.assertIsNone(application.guide_id)
        result.refresh_from_db()
        self.assertEqual(result.id, result_id)
        self.assertEqual(result.scope_origin, ScopeOrigin.GUIDE)

    def test_deleting_source_reference_removes_guide_but_keeps_applied_visit(self):
        self._entry(GuideEntryType.ITEM, self.child_item)
        application, _ = apply_guide(
            self.inspection, self.guide, self.inspector
        )
        frozen_id = self.inspection.master_version_id

        self.source.delete()

        self.inspection.refresh_from_db()
        application.refresh_from_db()
        self.assertIsNone(self.inspection.source_reference_id)
        self.assertEqual(self.inspection.master_version_id, frozen_id)
        self.assertIsNone(application.guide_id)
        self.assertTrue(
            InspectionItemResult.objects.filter(
                inspection_node__inspection=self.inspection,
                scope_origin=ScopeOrigin.GUIDE,
            ).exists()
        )

    def test_guide_from_other_reference_is_rejected(self):
        other_reference = MasterVersion.objects.create(
            number=99,
            name="مرجع آخر",
            visibility=ReferenceVisibility.SHARED,
            status=MasterStatus.PUBLISHED,
        )
        foreign_guide = Guide.objects.create(
            reference=other_reference,
            name="دليل أجنبي",
            created_by=self.admin,
        )
        with self.assertRaises(ValidationError):
            apply_guide(self.inspection, foreign_guide, self.inspector)

    def test_completed_visit_rejects_guide_application(self):
        self._entry(GuideEntryType.ITEM, self.child_item)
        self.inspection.status = InspectionStatus.COMPLETED
        self.inspection.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            apply_guide(self.inspection, self.guide, self.inspector)

    def test_admin_guide_pages_are_not_available_to_inspector(self):
        self.client.login(username="guide-inspector", password="test-pass-123")
        self.assertEqual(self.client.get(reverse("guide_list")).status_code, 403)
        self.assertEqual(
            self.client.get(reverse("guide_detail", args=[self.guide.pk])).status_code,
            403,
        )

    def test_inspection_guide_page_lists_only_compatible_guides(self):
        other_reference = MasterVersion.objects.create(
            number=100,
            name="مرجع مختلف",
            visibility=ReferenceVisibility.SHARED,
            status=MasterStatus.PUBLISHED,
        )
        Guide.objects.create(
            reference=other_reference,
            name="دليل غير متوافق",
            created_by=self.admin,
        )
        self.client.login(username="guide-inspector", password="test-pass-123")

        response = self.client.get(
            reverse("inspection_guides", args=[self.inspection.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.guide.name)
        self.assertNotContains(response, "دليل غير متوافق")

    def test_admin_cannot_apply_guide_to_inspector_draft(self):
        self._entry(GuideEntryType.ITEM, self.child_item)
        self.client.login(username="guide-admin", password="test-pass-123")

        response = self.client.post(
            reverse(
                "apply_inspection_guide",
                args=[self.inspection.pk, self.guide.pk],
            )
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            GuideApplication.objects.filter(inspection=self.inspection).exists()
        )

    def test_admin_cannot_add_hidden_target_under_inactive_parent(self):
        hidden_parent = StructureNode.objects.create(
            master_version=self.source,
            title="فرع معطل",
            active=False,
            sort_order=30,
        )
        hidden_child = StructureNode.objects.create(
            master_version=self.source,
            parent=hidden_parent,
            title="ابن نشط شكليًا",
            active=True,
        )
        hidden_item = ChecklistItem.objects.create(
            node=hidden_child,
            title="بند غير قابل للاختيار",
        )
        self.client.login(username="guide-admin", password="test-pass-123")

        response = self.client.post(
            reverse("guide_entry_add", args=[self.guide.pk]),
            {
                "entry_type": GuideEntryType.ITEM,
                "target_id": hidden_item.pk,
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            self.guide.entries.filter(stable_id=hidden_item.stable_id).exists()
        )

    def test_guide_creation_accepts_shared_reference_not_private_reference(self):
        private = MasterVersion.objects.create(
            number=200,
            name="مرجع خاص",
            visibility=ReferenceVisibility.PRIVATE,
            owner=self.inspector,
            status=MasterStatus.DRAFT,
        )
        self.client.login(username="guide-admin", password="test-pass-123")

        invalid = self.client.post(
            reverse("guide_create"),
            {
                "name": "دليل غير صالح",
                "description": "",
                "reference": private.pk,
            },
        )
        self.assertEqual(invalid.status_code, 200)
        self.assertFalse(Guide.objects.filter(name="دليل غير صالح").exists())

        valid = self.client.post(
            reverse("guide_create"),
            {
                "name": "دليل صالح",
                "description": "",
                "reference": self.source.pk,
            },
        )
        created = Guide.objects.get(name="دليل صالح")
        self.assertRedirects(valid, reverse("guide_detail", args=[created.pk]))
