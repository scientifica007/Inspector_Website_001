from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    ChecklistItem,
    Inspection,
    InspectionStatus,
    Institution,
    MasterStatus,
    MasterVersion,
    ReferenceVisibility,
    StructureNode,
)

User = get_user_model()


class InspectionDraftLifecycleTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user(
            "draft-owner", password="test-pass-123"
        )
        self.other = User.objects.create_user(
            "draft-other", password="test-pass-123"
        )
        self.admin = User.objects.create_superuser(
            "draft-admin", "admin@example.com", "test-pass-123"
        )
        self.institution = Institution.objects.create(name="مؤسسة المسودة")
        self.source = MasterVersion.objects.create(
            number=1,
            name="مرجع الزيارة الأصلي",
            visibility=ReferenceVisibility.SHARED,
            status=MasterStatus.PUBLISHED,
        )
        self.source_root = StructureNode.objects.create(
            master_version=self.source,
            title="المجال قبل إنشاء الزيارة",
            description="وصف أصلي",
            inspectable=True,
            sort_order=10,
        )
        self.source_item = ChecklistItem.objects.create(
            node=self.source_root,
            title="بند أصلي",
            guidance="توجيه أصلي",
            sort_order=10,
        )

    def create_from_source(self):
        self.client.login(username="draft-owner", password="test-pass-123")
        response = self.client.post(
            reverse("inspection_create"),
            {
                "institution": self.institution.id,
                "visit_date": "2026-09-19",
                "reference": self.source.id,
            },
        )
        inspection = Inspection.objects.get(inspector=self.inspector)
        self.assertRedirects(
            response,
            reverse("inspection_detail", args=[inspection.pk]),
        )
        return inspection

    def test_new_draft_freezes_reference_into_hidden_independent_copy(self):
        inspection = self.create_from_source()
        frozen = inspection.master_version

        self.assertEqual(inspection.source_reference, self.source)
        self.assertIsNotNone(frozen)
        self.assertNotEqual(frozen.id, self.source.id)
        self.assertEqual(frozen.visibility, ReferenceVisibility.SNAPSHOT)
        self.assertEqual(frozen.name, self.source.name)

        frozen_root = frozen.nodes.get()
        frozen_item = frozen_root.items.get()
        self.assertEqual(frozen_root.stable_id, self.source_root.stable_id)
        self.assertEqual(frozen_item.stable_id, self.source_item.stable_id)
        self.assertEqual(frozen_root.title, "المجال قبل إنشاء الزيارة")
        self.assertEqual(frozen_item.title, "بند أصلي")
        self.assertFalse(inspection.inspection_nodes.exists())

    def test_source_edits_after_creation_do_not_change_draft_choices(self):
        inspection = self.create_from_source()
        frozen = inspection.master_version
        frozen_item = frozen.nodes.get().items.get()

        self.source_root.title = "تعديل لاحق على المصدر"
        self.source_root.save(update_fields=["title"])
        self.source_item.title = "بند معدل لاحقًا"
        self.source_item.save(update_fields=["title"])

        response = self.client.get(reverse("inspection_scope", args=[inspection.pk]))
        self.assertContains(response, "المجال قبل إنشاء الزيارة")
        self.assertContains(response, "بند أصلي")
        self.assertNotContains(response, "تعديل لاحق على المصدر")
        self.assertNotContains(response, "بند معدل لاحقًا")

        response = self.client.post(
            reverse("inspection_scope", args=[inspection.pk]),
            {"action": "add_item", "source_item_id": frozen_item.id},
        )
        self.assertRedirects(
            response,
            reverse("inspection_scope", args=[inspection.pk]),
        )
        result = inspection.inspection_nodes.get().item_results.get()
        self.assertEqual(result.title_snapshot, "بند أصلي")

    def test_source_deletion_after_creation_does_not_break_draft(self):
        inspection = self.create_from_source()
        frozen_id = inspection.master_version_id

        self.source.delete()

        inspection.refresh_from_db()
        self.assertIsNone(inspection.source_reference_id)
        self.assertEqual(
            inspection.reference_name_snapshot,
            "مرجع الزيارة الأصلي",
        )
        self.assertEqual(inspection.master_version_id, frozen_id)
        self.assertTrue(
            MasterVersion.objects.filter(
                pk=frozen_id,
                visibility=ReferenceVisibility.SNAPSHOT,
            ).exists()
        )

        response = self.client.get(reverse("inspection_scope", args=[inspection.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "المجال قبل إنشاء الزيارة")
        self.assertContains(response, "بند أصلي")

    def test_owner_can_delete_draft_and_internal_snapshot_only(self):
        inspection = self.create_from_source()
        inspection_id = inspection.id
        frozen_id = inspection.master_version_id
        source_id = self.source.id

        confirm = self.client.get(reverse("inspection_delete", args=[inspection.id]))
        self.assertEqual(confirm.status_code, 200)
        self.assertContains(confirm, "حذف مسودة الزيارة")

        response = self.client.post(
            reverse("inspection_delete", args=[inspection.id])
        )
        self.assertRedirects(response, reverse("inspection_list"))
        self.assertFalse(Inspection.objects.filter(pk=inspection_id).exists())
        self.assertFalse(MasterVersion.objects.filter(pk=frozen_id).exists())
        self.assertTrue(MasterVersion.objects.filter(pk=source_id).exists())

    def test_completed_visit_cannot_be_deleted(self):
        inspection = self.create_from_source()
        frozen_id = inspection.master_version_id
        inspection.status = InspectionStatus.COMPLETED
        inspection.save(update_fields=["status"])

        response = self.client.post(
            reverse("inspection_delete", args=[inspection.id])
        )

        self.assertEqual(response.status_code, 409)
        self.assertTrue(Inspection.objects.filter(pk=inspection.id).exists())
        self.assertTrue(MasterVersion.objects.filter(pk=frozen_id).exists())

    def test_admin_cannot_delete_an_inspectors_draft(self):
        inspection = self.create_from_source()
        self.client.logout()
        self.client.login(username="draft-admin", password="test-pass-123")

        response = self.client.post(
            reverse("inspection_delete", args=[inspection.id])
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Inspection.objects.filter(pk=inspection.id).exists())

    def test_owner_can_delete_draft_created_without_reference(self):
        self.client.login(username="draft-owner", password="test-pass-123")
        response = self.client.post(
            reverse("inspection_create"),
            {
                "institution": self.institution.id,
                "visit_date": "2026-09-19",
                "reference": "",
            },
        )
        inspection = Inspection.objects.get(inspector=self.inspector)
        self.assertRedirects(
            response,
            reverse("inspection_detail", args=[inspection.pk]),
        )
        self.assertIsNone(inspection.master_version_id)

        response = self.client.post(
            reverse("inspection_delete", args=[inspection.id])
        )
        self.assertRedirects(response, reverse("inspection_list"))
        self.assertFalse(Inspection.objects.filter(pk=inspection.id).exists())
