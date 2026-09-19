from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    ChecklistItem,
    FieldType,
    MasterStatus,
    MasterVersion,
    ReferenceSubmission,
    ReferenceSubmissionStatus,
    ReferenceVisibility,
    SpecificationDefinition,
    StructureNode,
)
from .reference_library import (
    approve_reference_submission,
    clone_as_private,
    reject_reference_submission,
    submit_private_reference,
)
from .services import visible_references

User = get_user_model()


class PrivateReferenceSubmissionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            "reference-owner", password="test-pass-123"
        )
        self.other = User.objects.create_user(
            "reference-other", password="test-pass-123"
        )
        self.admin = User.objects.create_superuser(
            "reference-admin", "admin@example.com", "test-pass-123"
        )
        self.shared = MasterVersion.objects.create(
            number=1,
            name="مرجع مشترك أصلي",
            visibility=ReferenceVisibility.SHARED,
            status=MasterStatus.PUBLISHED,
        )
        self.root = StructureNode.objects.create(
            master_version=self.shared,
            title="المجال",
            description="وصف المجال",
            inspectable=False,
            sort_order=10,
        )
        SpecificationDefinition.objects.create(
            node=self.root,
            title="عدد العمال",
            field_type=FieldType.NUMBER,
            required=True,
            sort_order=10,
        )
        ChecklistItem.objects.create(
            node=self.root,
            title="سلامة التنظيم",
            guidance="تحقق",
            sort_order=20,
        )

    def test_private_reference_is_visible_only_to_owner_in_library(self):
        private = clone_as_private(self.shared, self.owner, name="مرجعي الخاص")

        self.assertTrue(visible_references(self.owner).filter(pk=private.pk).exists())
        self.assertFalse(visible_references(self.other).filter(pk=private.pk).exists())
        self.assertFalse(visible_references(self.admin).filter(pk=private.pk).exists())

        self.client.login(username="reference-other", password="test-pass-123")
        self.assertEqual(
            self.client.get(reverse("reference_detail", args=[private.pk])).status_code,
            404,
        )
        self.client.logout()
        self.client.login(username="reference-admin", password="test-pass-123")
        self.assertEqual(
            self.client.get(reverse("builder_reference", args=[private.pk])).status_code,
            404,
        )

    def test_clone_shared_reference_creates_independent_private_tree(self):
        clone = clone_as_private(self.shared, self.owner, name="نسختي")

        self.assertEqual(clone.visibility, ReferenceVisibility.PRIVATE)
        self.assertEqual(clone.owner, self.owner)
        copied_root = clone.nodes.get(title="المجال")
        self.assertNotEqual(copied_root.pk, self.root.pk)
        self.assertNotEqual(copied_root.stable_id, self.root.stable_id)
        self.assertFalse(copied_root.inspectable)
        self.assertEqual(copied_root.specifications.get().title, "عدد العمال")
        self.assertEqual(copied_root.items.get().title, "سلامة التنظيم")

        copied_root.title = "تعديل خاص"
        copied_root.save(update_fields=["title"])
        self.root.refresh_from_db()
        self.assertEqual(self.root.title, "المجال")

    def test_owner_can_edit_private_reference_through_builder_routes(self):
        private = clone_as_private(self.shared, self.owner, name="مرجعي")
        node = private.nodes.get(title="المجال")
        self.client.login(username="reference-owner", password="test-pass-123")
        response = self.client.post(
            reverse("builder_node_edit", args=[node.pk]),
            {
                "title": "مجال معدل",
                "description": "وصف المجال",
                "inspectable": "",
                "parent": "",
                "sort_order": 10,
                "active": "on",
            },
        )
        self.assertRedirects(response, reverse("builder_node", args=[node.pk]))
        node.refresh_from_db()
        self.assertEqual(node.title, "مجال معدل")

    def test_submission_is_frozen_snapshot_not_live_private_reference(self):
        private = clone_as_private(self.shared, self.owner, name="مرجعي")
        submission, created = submit_private_reference(private, self.owner)
        self.assertTrue(created)
        self.assertEqual(submission.snapshot["nodes"][0]["title"], "المجال")

        node = private.nodes.get(title="المجال")
        node.title = "تعديل بعد الإرسال"
        node.save(update_fields=["title"])

        submission.refresh_from_db()
        self.assertEqual(submission.snapshot["nodes"][0]["title"], "المجال")
        self.assertEqual(
            private.nodes.get(pk=node.pk).title,
            "تعديل بعد الإرسال",
        )

    def test_second_submit_while_pending_reuses_same_submission(self):
        private = clone_as_private(self.shared, self.owner, name="مرجعي")
        first, created = submit_private_reference(private, self.owner)
        self.assertTrue(created)
        second, created_again = submit_private_reference(private, self.owner)
        self.assertFalse(created_again)
        self.assertEqual(first.pk, second.pk)

    def test_rejection_leaves_private_reference_unchanged(self):
        private = clone_as_private(self.shared, self.owner, name="مرجعي")
        submission, _ = submit_private_reference(private, self.owner)

        rejected, changed = reject_reference_submission(
            submission,
            self.admin,
            note="لا يعتمد حاليًا",
        )

        self.assertTrue(changed)
        rejected.refresh_from_db()
        private.refresh_from_db()
        self.assertEqual(rejected.status, ReferenceSubmissionStatus.REJECTED)
        self.assertEqual(private.visibility, ReferenceVisibility.PRIVATE)
        self.assertEqual(private.owner, self.owner)
        self.assertFalse(
            MasterVersion.objects.filter(
                visibility=ReferenceVisibility.SHARED,
                name="مرجعي",
            ).exists()
        )

    def test_approval_creates_independent_shared_reference_from_frozen_snapshot(self):
        private = clone_as_private(self.shared, self.owner, name="مرجعي")
        submission, _ = submit_private_reference(private, self.owner)

        private_root = private.nodes.get(title="المجال")
        private_root.title = "تعديل خاص بعد الإرسال"
        private_root.save(update_fields=["title"])

        approved, changed = approve_reference_submission(
            submission,
            self.admin,
            shared_name="مرجع معتمد من الميدان",
            note="اعتماد",
        )

        self.assertTrue(changed)
        approved.refresh_from_db()
        shared = approved.resulting_reference
        self.assertEqual(approved.status, ReferenceSubmissionStatus.APPROVED)
        self.assertEqual(shared.visibility, ReferenceVisibility.SHARED)
        self.assertIsNone(shared.owner_id)
        self.assertEqual(shared.nodes.get().title, "المجال")
        private.refresh_from_db()
        self.assertEqual(private.visibility, ReferenceVisibility.PRIVATE)
        self.assertEqual(private.nodes.get(pk=private_root.pk).title, "تعديل خاص بعد الإرسال")
        self.assertTrue(visible_references(self.other).filter(pk=shared.pk).exists())

    def test_admin_reviews_submission_without_access_to_live_private_reference(self):
        private = clone_as_private(self.shared, self.owner, name="سري خاص")
        submission, _ = submit_private_reference(private, self.owner)
        self.client.login(username="reference-admin", password="test-pass-123")

        detail = self.client.get(
            reverse("reference_submission_detail", args=[submission.pk])
        )
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "المجال")
        self.assertNotContains(detail, "فتح المرجع الخاص")

        self.assertEqual(
            self.client.get(reverse("builder_reference", args=[private.pk])).status_code,
            404,
        )

    def test_private_reference_can_be_deleted_after_submission_without_losing_snapshot(self):
        private = clone_as_private(self.shared, self.owner, name="سيحذف")
        submission, _ = submit_private_reference(private, self.owner)
        private.delete()

        submission.refresh_from_db()
        self.assertIsNone(submission.source_reference_id)
        self.assertEqual(submission.source_name_snapshot, "سيحذف")
        self.assertEqual(submission.snapshot["nodes"][0]["title"], "المجال")
