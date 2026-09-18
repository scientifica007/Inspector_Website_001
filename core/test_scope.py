from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .governance import approve_proposal
from .models import (
    ChecklistItem,
    FieldType,
    Inspection,
    InspectionItemResult,
    InspectionScopeMode,
    InspectionStatus,
    Institution,
    MasterStatus,
    MasterVersion,
    Proposal,
    ProposalStatus,
    ProposalType,
    ResultStatus,
    ScopeOrigin,
    ScopeRole,
    ScopeState,
    SpecificationDefinition,
    StructureNode,
)
from .services import (
    add_scope_branch,
    add_scope_item,
    add_scope_specification,
    exclude_scope_item,
)

User = get_user_model()


class SelectiveScopeCoreTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user(
            "scope-inspector", password="test-pass-123"
        )
        self.other = User.objects.create_user(
            "scope-other", password="test-pass-123"
        )
        self.admin = User.objects.create_superuser(
            "scope-admin", "admin@example.com", "test-pass-123"
        )
        self.institution = Institution.objects.create(name="مؤسسة نطاق تجريبية")
        self.master = MasterVersion.objects.create(
            number=1, status=MasterStatus.PUBLISHED
        )
        self.root = StructureNode.objects.create(
            master_version=self.master,
            title="الإدارة",
            sort_order=10,
        )
        self.child = StructureNode.objects.create(
            master_version=self.master,
            parent=self.root,
            title="المصلحة",
            sort_order=10,
        )
        self.other_root = StructureNode.objects.create(
            master_version=self.master,
            title="الورشات",
            sort_order=20,
        )
        self.root_spec = SpecificationDefinition.objects.create(
            node=self.root,
            title="اسم المسؤول",
            field_type=FieldType.SHORT_TEXT,
            sort_order=10,
        )
        self.root_item = ChecklistItem.objects.create(
            node=self.root,
            title="بند الجذر",
            sort_order=10,
        )
        self.child_spec = SpecificationDefinition.objects.create(
            node=self.child,
            title="عدد الموظفين",
            field_type=FieldType.NUMBER,
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
        self.inspection = Inspection.objects.create(
            institution=self.institution,
            inspector=self.inspector,
            master_version=self.master,
            visit_date=date(2026, 9, 18),
        )

    def test_new_selective_inspection_starts_empty(self):
        self.assertEqual(self.inspection.scope_mode, InspectionScopeMode.SELECTIVE)
        self.assertFalse(self.inspection.inspection_nodes.exists())

    def test_single_item_adds_only_context_path_and_selected_item(self):
        result = add_scope_item(self.inspection, self.child_item)

        self.assertEqual(result.scope_origin, ScopeOrigin.MANUAL)
        self.assertEqual(result.scope_state, ScopeState.ACTIVE)
        self.assertEqual(self.inspection.inspection_nodes.count(), 2)

        root_snapshot = self.inspection.inspection_nodes.get(source_node=self.root)
        child_snapshot = self.inspection.inspection_nodes.get(source_node=self.child)
        self.assertEqual(root_snapshot.scope_role, ScopeRole.CONTEXT)
        self.assertEqual(child_snapshot.scope_role, ScopeRole.CONTEXT)
        self.assertEqual(child_snapshot.parent, root_snapshot)

        self.assertFalse(root_snapshot.specification_values.exists())
        self.assertFalse(root_snapshot.item_results.exists())
        self.assertFalse(child_snapshot.specification_values.exists())
        self.assertEqual(child_snapshot.item_results.count(), 1)
        self.assertFalse(
            self.inspection.inspection_nodes.filter(source_node=self.other_root).exists()
        )

    def test_single_specification_adds_context_without_unrelated_content(self):
        value = add_scope_specification(self.inspection, self.child_spec)
        child_snapshot = self.inspection.inspection_nodes.get(source_node=self.child)

        self.assertEqual(value.scope_state, ScopeState.ACTIVE)
        self.assertEqual(child_snapshot.scope_role, ScopeRole.CONTEXT)
        self.assertEqual(child_snapshot.specification_values.count(), 1)
        self.assertFalse(child_snapshot.item_results.exists())

    def test_branch_add_is_recursive_and_idempotent(self):
        add_scope_branch(self.inspection, self.root)
        first_node_count = self.inspection.inspection_nodes.count()
        first_item_count = InspectionItemResult.objects.filter(
            inspection_node__inspection=self.inspection
        ).count()

        add_scope_branch(self.inspection, self.root)

        self.assertEqual(self.inspection.inspection_nodes.count(), first_node_count)
        self.assertEqual(
            InspectionItemResult.objects.filter(
                inspection_node__inspection=self.inspection
            ).count(),
            first_item_count,
        )
        self.assertEqual(first_node_count, 2)
        root_snapshot = self.inspection.inspection_nodes.get(source_node=self.root)
        child_snapshot = self.inspection.inspection_nodes.get(source_node=self.child)
        self.assertEqual(root_snapshot.scope_role, ScopeRole.SELECTED)
        self.assertEqual(child_snapshot.scope_role, ScopeRole.SELECTED)
        self.assertEqual(root_snapshot.specification_values.count(), 1)
        self.assertEqual(child_snapshot.specification_values.count(), 1)

    def test_exclude_and_restore_item_preserves_same_snapshot_and_data(self):
        result = add_scope_item(self.inspection, self.child_item)
        snapshot_id = result.id
        result.status = ResultStatus.OBSERVATION
        result.observation = "بيانات يجب ألا تضيع"
        result.save(update_fields=["status", "observation"])

        exclude_scope_item(result)
        result.refresh_from_db()
        self.assertEqual(result.scope_state, ScopeState.EXCLUDED)
        self.assertEqual(
            self.inspection.inspection_nodes.get(source_node=self.child).scope_state,
            ScopeState.EXCLUDED,
        )
        self.assertEqual(
            self.inspection.inspection_nodes.get(source_node=self.root).scope_state,
            ScopeState.EXCLUDED,
        )

        restored = add_scope_item(self.inspection, self.child_item)
        self.assertEqual(restored.id, snapshot_id)
        self.assertEqual(restored.status, ResultStatus.OBSERVATION)
        self.assertEqual(restored.observation, "بيانات يجب ألا تضيع")
        self.assertEqual(restored.scope_state, ScopeState.ACTIVE)
        self.assertEqual(
            self.inspection.inspection_nodes.get(source_node=self.child).scope_role,
            ScopeRole.CONTEXT,
        )


    def test_context_node_is_navigable_for_selected_direct_item(self):
        result = add_scope_item(self.inspection, self.child_item)
        child_snapshot = self.inspection.inspection_nodes.get(source_node=self.child)
        self.assertEqual(child_snapshot.scope_role, ScopeRole.CONTEXT)

        self.client.login(username="scope-inspector", password="test-pass-123")
        response = self.client.get(
            reverse("inspection_node", args=[self.inspection.pk, child_snapshot.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "بند المصلحة")
        self.assertFalse(response.context["node_notes_enabled"])

        response = self.client.post(
            reverse("inspection_node", args=[self.inspection.pk, child_snapshot.pk]),
            {
                f"status_{result.id}": ResultStatus.OBSERVATION,
                f"observation_{result.id}": "ملاحظة من عنصر منفرد",
            },
        )
        self.assertRedirects(
            response,
            reverse("inspection_node", args=[self.inspection.pk, child_snapshot.pk]),
        )
        result.refresh_from_db()
        self.assertEqual(result.status, ResultStatus.OBSERVATION)
        self.assertEqual(result.observation, "ملاحظة من عنصر منفرد")

    def test_local_item_can_be_added_inside_context_node(self):
        add_scope_item(self.inspection, self.child_item)
        child_snapshot = self.inspection.inspection_nodes.get(source_node=self.child)
        self.client.login(username="scope-inspector", password="test-pass-123")

        response = self.client.post(
            reverse("local_item_add", args=[self.inspection.pk, child_snapshot.pk]),
            {"title": "بند محلي داخل السياق", "guidance": ""},
        )
        self.assertRedirects(
            response,
            reverse("inspection_node_prepare", args=[self.inspection.pk, child_snapshot.pk]),
        )
        local = child_snapshot.item_results.get(title_snapshot="بند محلي داخل السياق")
        self.assertEqual(local.scope_origin, ScopeOrigin.LOCAL)
        self.assertEqual(
            Proposal.objects.filter(
                source_inspection=self.inspection,
                proposal_type=ProposalType.ITEM,
                source_local_id=local.id,
            ).count(),
            1,
        )

    def test_locked_item_cannot_be_excluded(self):
        result = add_scope_item(
            self.inspection,
            self.child_item,
            origin=ScopeOrigin.ASSIGNMENT,
            locked=True,
        )
        with self.assertRaises(ValidationError):
            exclude_scope_item(result)
        result.refresh_from_db()
        self.assertEqual(result.scope_state, ScopeState.ACTIVE)

    def test_progress_uses_active_scope_only(self):
        first = add_scope_item(self.inspection, self.root_item)
        second = add_scope_item(self.inspection, self.child_item)
        first.status = ResultStatus.COMPLIANT
        first.save(update_fields=["status"])
        exclude_scope_item(second)

        self.client.login(username="scope-inspector", password="test-pass-123")
        response = self.client.get(reverse("inspection_detail", args=[self.inspection.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_items"], 1)
        self.assertEqual(response.context["resolved_items"], 1)
        self.assertEqual(response.context["progress"], 100)

    def test_completion_required_blocks_completion_until_resolved(self):
        result = add_scope_item(
            self.inspection,
            self.child_item,
            origin=ScopeOrigin.ASSIGNMENT,
            locked=True,
            completion_required=True,
        )
        self.client.login(username="scope-inspector", password="test-pass-123")

        response = self.client.post(
            reverse("inspection_complete", args=[self.inspection.pk]),
            {"confirm": "on"},
        )
        self.assertEqual(response.status_code, 200)
        self.inspection.refresh_from_db()
        self.assertEqual(self.inspection.status, InspectionStatus.DRAFT)
        self.assertContains(response, "لا يمكن إنهاء الزيارة")

        result.status = ResultStatus.COMPLIANT
        result.save(update_fields=["status"])
        response = self.client.post(
            reverse("inspection_complete", args=[self.inspection.pk]),
            {"confirm": "on"},
        )
        self.assertRedirects(
            response, reverse("inspection_detail", args=[self.inspection.pk])
        )
        self.inspection.refresh_from_db()
        self.assertEqual(self.inspection.status, InspectionStatus.COMPLETED)

    def test_scope_manager_allows_owner_and_denies_other_inspector(self):
        self.client.login(username="scope-inspector", password="test-pass-123")
        response = self.client.post(
            reverse("inspection_scope", args=[self.inspection.pk]),
            {"action": "add_item", "source_item_id": self.child_item.id},
        )
        self.assertRedirects(
            response, reverse("inspection_scope", args=[self.inspection.pk])
        )
        self.assertTrue(
            InspectionItemResult.objects.filter(
                inspection_node__inspection=self.inspection,
                source_item=self.child_item,
                scope_state=ScopeState.ACTIVE,
            ).exists()
        )

        self.client.logout()
        self.client.login(username="scope-other", password="test-pass-123")
        self.assertEqual(
            self.client.get(
                reverse("inspection_scope", args=[self.inspection.pk])
            ).status_code,
            404,
        )

    def test_reference_from_other_master_is_rejected(self):
        other_master = MasterVersion.objects.create(
            number=2, status=MasterStatus.ARCHIVED
        )
        other_node = StructureNode.objects.create(
            master_version=other_master,
            title="مرجع آخر",
        )
        foreign_item = ChecklistItem.objects.create(
            node=other_node,
            title="بند أجنبي",
        )
        with self.assertRaises(ValidationError):
            add_scope_item(self.inspection, foreign_item)

    def test_local_root_is_immediate_and_approves_to_draft_root(self):
        self.client.login(username="scope-inspector", password="test-pass-123")
        response = self.client.post(
            reverse("local_root_node_add", args=[self.inspection.pk]),
            {
                "title": "عنصر ميداني رئيسي",
                "description": "غير موجود في المرجع",
                "inspectable": "on",
            },
        )
        local = self.inspection.inspection_nodes.get(
            title_snapshot="عنصر ميداني رئيسي"
        )
        self.assertRedirects(
            response,
            reverse("inspection_node_prepare", args=[self.inspection.pk, local.pk]),
        )
        self.assertIsNone(local.parent_id)
        self.assertEqual(local.scope_origin, ScopeOrigin.LOCAL)
        proposal = Proposal.objects.get(
            proposal_type=ProposalType.NODE,
            source_inspection=self.inspection,
            source_local_id=local.id,
        )
        self.assertEqual(proposal.status, ProposalStatus.PENDING)
        self.assertTrue(proposal.payload["target_root"])

        approved, changed = approve_proposal(
            proposal,
            self.admin,
            dict(proposal.payload),
            "اعتماد الجذر المحلي",
        )
        self.assertTrue(changed)
        approved.refresh_from_db()
        self.assertEqual(approved.status, ProposalStatus.APPROVED)
        draft = MasterVersion.objects.get(status=MasterStatus.DRAFT)
        created = StructureNode.objects.get(
            master_version=draft,
            title="عنصر ميداني رئيسي",
        )
        self.assertIsNone(created.parent_id)
