import uuid
from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .assignments import issue_assignment, revoke_assignment
from .exporting import build_inspection_export
from .models import (
    Assignment,
    AssignmentEffect,
    AssignmentEntry,
    AssignmentEntryType,
    AssignmentStatus,
    ChecklistItem,
    FieldType,
    Inspection,
    InspectionItemResult,
    InspectionStatus,
    Institution,
    MasterStatus,
    MasterVersion,
    ReferenceVisibility,
    ResultStatus,
    ScopeOrigin,
    SpecificationDefinition,
    SpecificationValue,
    StructureNode,
)
from .reference_library import freeze_reference_for_inspection
from .services import (
    add_scope_item,
    exclude_scope_item,
    incomplete_required_scope_count,
)

User = get_user_model()


class RequiredAssignmentTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user(
            "assignment-inspector", password="test-pass-123"
        )
        self.other = User.objects.create_user(
            "assignment-other", password="test-pass-123"
        )
        self.admin = User.objects.create_superuser(
            "assignment-admin", "admin@example.com", "test-pass-123"
        )
        self.institution = Institution.objects.create(name="مؤسسة التكليف")
        self.source = MasterVersion.objects.create(
            number=1,
            name="مرجع التكليف",
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
        frozen = freeze_reference_for_inspection(self.source)
        self.inspection = Inspection.objects.create(
            institution=self.institution,
            inspector=self.inspector,
            master_version=frozen,
            source_reference=self.source,
            reference_name_snapshot=self.source.name,
            visit_date=date(2026, 9, 19),
        )

    def assignment(self, title="تكليف اختبار"):
        return Assignment.objects.create(
            inspection=self.inspection,
            title=title,
            description="تعليمات رسمية",
            created_by=self.admin,
        )

    def entry(
        self,
        assignment,
        entry_type,
        source_obj,
        *,
        locked=False,
        required=False,
        order=10,
    ):
        return AssignmentEntry.objects.create(
            assignment=assignment,
            entry_type=entry_type,
            stable_id=source_obj.stable_id,
            label_snapshot=source_obj.title,
            scope_locked=locked,
            completion_required=required,
            sort_order=order,
        )

    def frozen_item(self, source_item):
        return ChecklistItem.objects.get(
            node__master_version=self.inspection.master_version,
            stable_id=source_item.stable_id,
        )

    def test_item_assignment_adds_context_and_both_obligations(self):
        assignment = self.assignment()
        self.entry(
            assignment,
            AssignmentEntryType.ITEM,
            self.child_item,
            locked=True,
            required=True,
        )

        issue_assignment(assignment, self.admin)

        assignment.refresh_from_db()
        self.assertEqual(assignment.status, AssignmentStatus.ISSUED)
        self.assertEqual(self.inspection.inspection_nodes.count(), 2)

        result = InspectionItemResult.objects.get(
            inspection_node__inspection=self.inspection,
            source_item__stable_id=self.child_item.stable_id,
        )
        self.assertEqual(result.scope_origin, ScopeOrigin.ASSIGNMENT)
        self.assertTrue(result.scope_locked)
        self.assertTrue(result.completion_required)
        self.assertEqual(incomplete_required_scope_count(self.inspection), 1)

        with self.assertRaises(ValidationError):
            exclude_scope_item(result)

        result.status = ResultStatus.COMPLIANT
        result.save(update_fields=["status"])
        self.assertEqual(incomplete_required_scope_count(self.inspection), 0)

    def test_branch_assignment_locks_structure_and_requires_leaf_work(self):
        assignment = self.assignment()
        self.entry(
            assignment,
            AssignmentEntryType.BRANCH,
            self.root,
            locked=True,
            required=True,
        )

        issue_assignment(assignment, self.admin)

        nodes = self.inspection.inspection_nodes.all()
        self.assertEqual(nodes.count(), 2)
        self.assertTrue(all(node.scope_locked for node in nodes))
        self.assertTrue(
            all(
                value.scope_locked and value.completion_required
                for value in SpecificationValue.objects.filter(
                    inspection_node__inspection=self.inspection
                )
            )
        )
        self.assertTrue(
            all(
                item.scope_locked and item.completion_required
                for item in InspectionItemResult.objects.filter(
                    inspection_node__inspection=self.inspection
                )
            )
        )
        self.assertEqual(incomplete_required_scope_count(self.inspection), 4)

    def test_branch_completion_only_does_not_lock_scope(self):
        assignment = self.assignment()
        self.entry(
            assignment,
            AssignmentEntryType.BRANCH,
            self.root,
            required=True,
        )

        issue_assignment(assignment, self.admin)

        self.assertFalse(
            self.inspection.inspection_nodes.filter(scope_locked=True).exists()
        )
        self.assertFalse(
            SpecificationValue.objects.filter(
                inspection_node__inspection=self.inspection,
                scope_locked=True,
            ).exists()
        )
        self.assertFalse(
            InspectionItemResult.objects.filter(
                inspection_node__inspection=self.inspection,
                scope_locked=True,
            ).exists()
        )
        self.assertEqual(incomplete_required_scope_count(self.inspection), 4)

    def test_existing_manual_item_keeps_origin_when_assignment_overlaps(self):
        manual = add_scope_item(
            self.inspection,
            self.frozen_item(self.child_item),
            origin=ScopeOrigin.MANUAL,
        )
        assignment = self.assignment()
        self.entry(
            assignment,
            AssignmentEntryType.ITEM,
            self.child_item,
            locked=True,
        )

        issue_assignment(assignment, self.admin)

        manual.refresh_from_db()
        self.assertEqual(manual.scope_origin, ScopeOrigin.MANUAL)
        self.assertTrue(manual.scope_locked)
        self.assertFalse(manual.completion_required)

    def test_overlapping_assignments_recompute_independent_obligations(self):
        first = self.assignment("قيد النطاق")
        second = self.assignment("إلزام الإكمال")
        self.entry(
            first,
            AssignmentEntryType.ITEM,
            self.child_item,
            locked=True,
        )
        self.entry(
            second,
            AssignmentEntryType.ITEM,
            self.child_item,
            required=True,
        )

        issue_assignment(first, self.admin)
        issue_assignment(second, self.admin)
        result = InspectionItemResult.objects.get(
            inspection_node__inspection=self.inspection,
            source_item__stable_id=self.child_item.stable_id,
        )
        self.assertTrue(result.scope_locked)
        self.assertTrue(result.completion_required)

        revoke_assignment(first, self.admin, "انتهى سبب القيد")
        result.refresh_from_db()
        self.assertFalse(result.scope_locked)
        self.assertTrue(result.completion_required)

        revoke_assignment(second, self.admin, "انتهى سبب الإلزام")
        result.refresh_from_db()
        self.assertFalse(result.scope_locked)
        self.assertFalse(result.completion_required)

    def test_baseline_constraint_survives_assignment_revocation(self):
        result = add_scope_item(
            self.inspection,
            self.frozen_item(self.child_item),
            origin=ScopeOrigin.MANUAL,
            locked=True,
            completion_required=True,
        )
        self.assertTrue(result.base_scope_locked)
        self.assertTrue(result.base_completion_required)

        assignment = self.assignment()
        self.entry(
            assignment,
            AssignmentEntryType.ITEM,
            self.child_item,
            locked=True,
            required=True,
        )
        issue_assignment(assignment, self.admin)
        revoke_assignment(assignment, self.admin, "إلغاء التكليف فقط")

        result.refresh_from_db()
        self.assertTrue(result.scope_locked)
        self.assertTrue(result.completion_required)

    def test_revocation_keeps_same_snapshot_and_field_data(self):
        result = add_scope_item(
            self.inspection,
            self.frozen_item(self.child_item),
            origin=ScopeOrigin.MANUAL,
        )
        result.status = ResultStatus.OBSERVATION
        result.observation = "بيانات ميدانية محفوظة"
        result.save(update_fields=["status", "observation"])
        original_id = result.id

        assignment = self.assignment()
        self.entry(
            assignment,
            AssignmentEntryType.ITEM,
            self.child_item,
            locked=True,
            required=True,
        )
        issue_assignment(assignment, self.admin)
        revoke_assignment(assignment, self.admin, "تصحيح التكليف")

        result.refresh_from_db()
        self.assertEqual(result.id, original_id)
        self.assertEqual(result.status, ResultStatus.OBSERVATION)
        self.assertEqual(result.observation, "بيانات ميدانية محفوظة")
        self.assertFalse(result.scope_locked)
        self.assertFalse(result.completion_required)

    def test_issue_is_atomic_when_any_entry_cannot_resolve(self):
        assignment = self.assignment()
        self.entry(
            assignment,
            AssignmentEntryType.ITEM,
            self.child_item,
            locked=True,
        )
        AssignmentEntry.objects.create(
            assignment=assignment,
            entry_type=AssignmentEntryType.ITEM,
            stable_id=uuid.uuid4(),
            label_snapshot="عنصر غير موجود في اللقطة",
            scope_locked=True,
            sort_order=20,
        )

        with self.assertRaises(ValidationError):
            issue_assignment(assignment, self.admin)

        assignment.refresh_from_db()
        self.assertEqual(assignment.status, AssignmentStatus.DRAFT)
        self.assertFalse(self.inspection.inspection_nodes.exists())
        self.assertFalse(
            AssignmentEffect.objects.filter(
                assignment_entry__assignment=assignment
            ).exists()
        )

    def test_empty_assignment_cannot_be_issued(self):
        assignment = self.assignment()
        with self.assertRaises(ValidationError):
            issue_assignment(assignment, self.admin)
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, AssignmentStatus.DRAFT)

    def test_completed_visit_blocks_issue_and_revoke(self):
        draft_assignment = self.assignment("لن يصدر")
        self.entry(
            draft_assignment,
            AssignmentEntryType.ITEM,
            self.child_item,
            locked=True,
        )
        self.inspection.status = InspectionStatus.COMPLETED
        self.inspection.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            issue_assignment(draft_assignment, self.admin)

        self.inspection.status = InspectionStatus.DRAFT
        self.inspection.save(update_fields=["status"])
        issue_assignment(draft_assignment, self.admin)
        self.inspection.status = InspectionStatus.COMPLETED
        self.inspection.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            revoke_assignment(draft_assignment, self.admin, "غير مسموح")

    def test_revocation_requires_reason(self):
        assignment = self.assignment()
        self.entry(
            assignment,
            AssignmentEntryType.ITEM,
            self.child_item,
            locked=True,
        )
        issue_assignment(assignment, self.admin)

        with self.assertRaises(ValidationError):
            revoke_assignment(assignment, self.admin, "   ")

        assignment.refresh_from_db()
        self.assertEqual(assignment.status, AssignmentStatus.ISSUED)

    def test_assignment_completion_obligation_blocks_visit_completion(self):
        assignment = self.assignment()
        self.entry(
            assignment,
            AssignmentEntryType.ITEM,
            self.child_item,
            required=True,
        )
        issue_assignment(assignment, self.admin)

        self.client.login(
            username="assignment-inspector",
            password="test-pass-123",
        )
        response = self.client.post(
            reverse("inspection_complete", args=[self.inspection.pk]),
            {"confirm": "on"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "لا يمكن إنهاء الزيارة")

        result = InspectionItemResult.objects.get(
            inspection_node__inspection=self.inspection,
            source_item__stable_id=self.child_item.stable_id,
        )
        result.status = ResultStatus.NOT_APPLICABLE
        result.save(update_fields=["status"])

        response = self.client.post(
            reverse("inspection_complete", args=[self.inspection.pk]),
            {"confirm": "on"},
        )
        self.assertRedirects(
            response,
            reverse("inspection_detail", args=[self.inspection.pk]),
        )
        self.inspection.refresh_from_db()
        self.assertEqual(self.inspection.status, InspectionStatus.COMPLETED)

    def test_inspector_cannot_see_admin_draft_but_sees_issued_assignment(self):
        assignment = self.assignment()
        self.entry(
            assignment,
            AssignmentEntryType.ITEM,
            self.child_item,
            locked=True,
        )
        self.client.login(
            username="assignment-inspector",
            password="test-pass-123",
        )

        listing = self.client.get(
            reverse("inspection_assignments", args=[self.inspection.pk])
        )
        self.assertEqual(listing.status_code, 200)
        self.assertNotContains(listing, assignment.title)
        self.assertEqual(
            self.client.get(
                reverse("assignment_detail", args=[assignment.pk])
            ).status_code,
            404,
        )

        issue_assignment(assignment, self.admin)
        listing = self.client.get(
            reverse("inspection_assignments", args=[self.inspection.pk])
        )
        self.assertContains(listing, assignment.title)
        detail = self.client.get(
            reverse("assignment_detail", args=[assignment.pk])
        )
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "مقيد في النطاق")

    def test_inspector_cannot_issue_or_mutate_assignment(self):
        assignment = self.assignment()
        self.entry(
            assignment,
            AssignmentEntryType.ITEM,
            self.child_item,
            locked=True,
        )
        self.client.login(
            username="assignment-inspector",
            password="test-pass-123",
        )
        self.assertEqual(
            self.client.post(
                reverse("assignment_issue", args=[assignment.pk])
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("assignment_entry_add", args=[assignment.pk]),
                {
                    "entry_type": AssignmentEntryType.ITEM,
                    "target_id": self.frozen_item(self.root_item).pk,
                    "scope_locked": "on",
                },
            ).status_code,
            403,
        )

    def test_entry_requires_at_least_one_obligation_in_ui(self):
        assignment = self.assignment()
        frozen = self.frozen_item(self.child_item)
        self.client.login(
            username="assignment-admin",
            password="test-pass-123",
        )
        response = self.client.post(
            reverse("assignment_entry_add", args=[assignment.pk]),
            {
                "entry_type": AssignmentEntryType.ITEM,
                "target_id": frozen.pk,
            },
        )
        self.assertRedirects(
            response,
            reverse("assignment_detail", args=[assignment.pk]),
        )
        self.assertFalse(assignment.entries.exists())

    def test_issued_assignment_structure_cannot_be_modified(self):
        assignment = self.assignment()
        entry = self.entry(
            assignment,
            AssignmentEntryType.ITEM,
            self.child_item,
            locked=True,
        )
        issue_assignment(assignment, self.admin)
        frozen = self.frozen_item(self.root_item)
        self.client.login(
            username="assignment-admin",
            password="test-pass-123",
        )

        self.assertEqual(
            self.client.post(
                reverse("assignment_entry_add", args=[assignment.pk]),
                {
                    "entry_type": AssignmentEntryType.ITEM,
                    "target_id": frozen.pk,
                    "scope_locked": "on",
                },
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse(
                    "assignment_entry_delete",
                    args=[assignment.pk, entry.pk],
                )
            ).status_code,
            404,
        )

    def test_assignment_export_contains_issued_and_revoked_audit_history(self):
        assignment = self.assignment("تكليف التصدير")
        entry = self.entry(
            assignment,
            AssignmentEntryType.ITEM,
            self.child_item,
            locked=True,
            required=True,
        )
        issue_assignment(assignment, self.admin)

        payload = build_inspection_export(self.inspection)
        exported = payload["inspection"]["assignments"][0]
        self.assertEqual(payload["schema"], "inspection-export-v4")
        self.assertEqual(exported["title"], "تكليف التصدير")
        self.assertEqual(exported["status"], AssignmentStatus.ISSUED)
        self.assertTrue(exported["entries"][0]["scope_locked"])
        self.assertTrue(exported["entries"][0]["completion_required"])
        self.assertEqual(
            exported["entries"][0]["stable_id"],
            str(entry.stable_id),
        )

        revoke_assignment(assignment, self.admin, "أُلغي رسميًا")
        exported = build_inspection_export(
            self.inspection
        )["inspection"]["assignments"][0]
        self.assertEqual(exported["status"], AssignmentStatus.REVOKED)
        self.assertEqual(exported["revocation_reason"], "أُلغي رسميًا")

    def test_admin_cannot_create_assignment_for_visit_without_reference(self):
        blank = Inspection.objects.create(
            institution=self.institution,
            inspector=self.inspector,
            visit_date=date(2026, 9, 20),
        )
        self.client.login(
            username="assignment-admin",
            password="test-pass-123",
        )
        response = self.client.get(
            reverse("assignment_create", args=[blank.pk])
        )
        self.assertEqual(response.status_code, 403)
