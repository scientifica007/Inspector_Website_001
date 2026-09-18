from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .governance import approve_proposal
from .local_authoring import (
    copy_item_as_local,
    copy_node_as_local,
    move_local_item,
    move_local_node,
    remove_local_item,
    restore_local_item,
    sync_local_proposal,
    update_local_item,
    update_local_specification,
)
from .models import (
    ChecklistItem,
    FieldType,
    Inspection,
    InspectionItemResult,
    InspectionNode,
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
    SpecificationValue,
    StructureNode,
)
from .services import add_scope_branch


User = get_user_model()


class LocalAuthoringOperationsTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user(
            "authoring-inspector", password="test-pass-123"
        )
        self.other = User.objects.create_user(
            "authoring-other", password="test-pass-123"
        )
        self.admin = User.objects.create_superuser(
            "authoring-admin", "admin@example.com", "test-pass-123"
        )
        self.institution = Institution.objects.create(name="مؤسسة التأليف")
        self.master = MasterVersion.objects.create(
            number=1,
            status=MasterStatus.PUBLISHED,
        )
        self.root = StructureNode.objects.create(
            master_version=self.master,
            title="المديرية",
            sort_order=10,
        )
        self.child = StructureNode.objects.create(
            master_version=self.master,
            parent=self.root,
            title="المصلحة",
            sort_order=20,
        )
        self.root_spec = SpecificationDefinition.objects.create(
            node=self.root,
            title="عدد العمال",
            field_type=FieldType.NUMBER,
            required=True,
            sort_order=10,
        )
        self.root_item = ChecklistItem.objects.create(
            node=self.root,
            title="سلامة التنظيم",
            guidance="تحقق من الوثائق",
            sort_order=10,
        )
        ChecklistItem.objects.create(
            node=self.child,
            title="سجل النشاط",
            sort_order=10,
        )
        self.inspection = Inspection.objects.create(
            institution=self.institution,
            inspector=self.inspector,
            master_version=self.master,
            visit_date=date(2026, 9, 18),
        )
        add_scope_branch(self.inspection, self.root)
        self.snap_root = self.inspection.inspection_nodes.get(source_node=self.root)
        self.snap_child = self.inspection.inspection_nodes.get(source_node=self.child)

    def local_item(self, node=None, title="بند محلي"):
        node = node or self.snap_root
        item = InspectionItemResult.objects.create(
            inspection_node=node,
            title_snapshot=title,
            guidance_snapshot="توجيه محلي",
            sort_order_snapshot=90,
            scope_origin=ScopeOrigin.LOCAL,
            scope_state=ScopeState.ACTIVE,
        )
        sync_local_proposal(item, self.inspector)
        return item

    def local_spec(self, node=None, title="وصف محلي"):
        node = node or self.snap_root
        value = SpecificationValue.objects.create(
            inspection_node=node,
            title_snapshot=title,
            field_type_snapshot=FieldType.NUMBER,
            required_snapshot=True,
            options_snapshot=[],
            help_text_snapshot="مساعدة",
            sort_order_snapshot=90,
            scope_origin=ScopeOrigin.LOCAL,
            scope_state=ScopeState.ACTIVE,
        )
        sync_local_proposal(value, self.inspector)
        return value

    def local_node(self, parent=None, title="فرع محلي"):
        parent = self.snap_root if parent is None else parent
        node = InspectionNode.objects.create(
            inspection=self.inspection,
            parent=parent,
            title_snapshot=title,
            description_snapshot="وصف الفرع",
            sort_order_snapshot=90,
            scope_origin=ScopeOrigin.LOCAL,
            scope_state=ScopeState.ACTIVE,
            scope_role=ScopeRole.SELECTED,
        )
        sync_local_proposal(node, self.inspector, inspectable=True)
        return node

    def test_pending_edit_updates_same_proposal(self):
        item = self.local_item()
        proposal = Proposal.objects.get(
            proposal_type=ProposalType.ITEM,
            source_local_id=item.id,
        )

        update_local_item(
            item,
            self.inspector,
            {"title": "عنوان معدل", "guidance": "توجيه معدل"},
        )

        item.refresh_from_db()
        proposal.refresh_from_db()
        self.assertEqual(item.title_snapshot, "عنوان معدل")
        self.assertEqual(proposal.status, ProposalStatus.PENDING)
        self.assertEqual(proposal.payload["title"], "عنوان معدل")
        self.assertEqual(
            Proposal.objects.filter(
                proposal_type=ProposalType.ITEM,
                source_local_id=item.id,
            ).count(),
            1,
        )

    def test_edit_after_resolution_creates_new_pending_proposal(self):
        item = self.local_item()
        first = Proposal.objects.get(
            proposal_type=ProposalType.ITEM,
            source_local_id=item.id,
        )
        approve_proposal(first, self.admin, dict(first.payload), "اعتماد أول")

        update_local_item(
            item,
            self.inspector,
            {"title": "تعديل لاحق", "guidance": "بعد الاعتماد"},
        )

        first.refresh_from_db()
        proposals = Proposal.objects.filter(
            proposal_type=ProposalType.ITEM,
            source_local_id=item.id,
        ).order_by("id")
        self.assertEqual(first.status, ProposalStatus.APPROVED)
        self.assertEqual(proposals.count(), 2)
        self.assertEqual(proposals.last().status, ProposalStatus.PENDING)
        self.assertEqual(proposals.last().payload["title"], "تعديل لاحق")

    def test_remove_withdraws_pending_and_restore_reproposes_without_data_loss(self):
        item = self.local_item()
        item.status = ResultStatus.OBSERVATION
        item.observation = "بيانات يجب أن تبقى"
        item.save(update_fields=["status", "observation"])
        original_id = item.id

        remove_local_item(item, self.inspector)
        item.refresh_from_db()
        withdrawn = Proposal.objects.get(
            proposal_type=ProposalType.ITEM,
            source_local_id=item.id,
        )
        self.assertEqual(item.scope_state, ScopeState.EXCLUDED)
        self.assertEqual(withdrawn.status, ProposalStatus.WITHDRAWN)

        restore_local_item(item, self.inspector)
        item.refresh_from_db()
        proposals = Proposal.objects.filter(
            proposal_type=ProposalType.ITEM,
            source_local_id=item.id,
        ).order_by("id")
        self.assertEqual(item.id, original_id)
        self.assertEqual(item.scope_state, ScopeState.ACTIVE)
        self.assertEqual(item.status, ResultStatus.OBSERVATION)
        self.assertEqual(item.observation, "بيانات يجب أن تبقى")
        self.assertEqual(proposals.count(), 2)
        self.assertEqual(proposals.last().status, ProposalStatus.PENDING)

    def test_description_type_change_clears_incompatible_field_value(self):
        value = self.local_spec()
        value.value = 15
        value.save(update_fields=["value"])

        update_local_specification(
            value,
            self.inspector,
            {
                "title": "تاريخ المعاينة",
                "field_type": FieldType.DATE,
                "required": True,
                "options": [],
                "help_text": "",
            },
        )

        value.refresh_from_db()
        self.assertEqual(value.field_type_snapshot, FieldType.DATE)
        self.assertIsNone(value.value)

    def test_copy_reference_item_as_local_resets_field_result(self):
        source = self.snap_root.item_results.get(source_item=self.root_item)
        source.status = ResultStatus.NON_COMPLIANT
        source.observation = "نتيجة أصلية"
        source.save(update_fields=["status", "observation"])

        clone = copy_item_as_local(source, self.snap_child, self.inspector)

        source.refresh_from_db()
        self.assertIsNone(clone.source_item_id)
        self.assertEqual(clone.scope_origin, ScopeOrigin.LOCAL)
        self.assertEqual(clone.inspection_node_id, self.snap_child.id)
        self.assertEqual(clone.status, ResultStatus.UNCHECKED)
        self.assertEqual(clone.observation, "")
        self.assertEqual(source.status, ResultStatus.NON_COMPLIANT)
        self.assertEqual(source.observation, "نتيجة أصلية")
        self.assertTrue(
            Proposal.objects.filter(
                proposal_type=ProposalType.ITEM,
                source_local_id=clone.id,
                status=ProposalStatus.PENDING,
            ).exists()
        )

    def test_move_local_item_preserves_field_data_and_updates_pending_target(self):
        item = self.local_item()
        item.status = ResultStatus.COMPLIANT
        item.observation = "محفوظ"
        item.save(update_fields=["status", "observation"])

        moved, changed = move_local_item(
            item,
            self.snap_child,
            self.inspector,
        )

        self.assertTrue(changed)
        moved.refresh_from_db()
        proposal = Proposal.objects.get(
            proposal_type=ProposalType.ITEM,
            source_local_id=item.id,
            status=ProposalStatus.PENDING,
        )
        self.assertEqual(moved.inspection_node_id, self.snap_child.id)
        self.assertEqual(moved.status, ResultStatus.COMPLIANT)
        self.assertEqual(moved.observation, "محفوظ")
        self.assertEqual(
            proposal.payload["target_node_stable_id"],
            str(self.child.stable_id),
        )

    def test_branch_copy_is_recursive_local_and_resets_field_results(self):
        branch = self.local_node(title="فرع قابل للنسخ")
        value = self.local_spec(branch, title="وصف داخل الفرع")
        value.value = 44
        value.save(update_fields=["value"])
        item = self.local_item(branch, title="بند داخل الفرع")
        item.status = ResultStatus.NON_COMPLIANT
        item.observation = "لا تُنسخ"
        item.save(update_fields=["status", "observation"])
        child = self.local_node(branch, title="فرع تابع")

        clone = copy_node_as_local(branch, self.snap_root, self.inspector)

        self.assertNotEqual(clone.id, branch.id)
        self.assertEqual(clone.scope_origin, ScopeOrigin.LOCAL)
        self.assertIsNone(clone.source_node_id)
        copied_value = clone.specification_values.get(title_snapshot="وصف داخل الفرع")
        copied_item = clone.item_results.get(title_snapshot="بند داخل الفرع")
        copied_child = clone.children.get(title_snapshot="فرع تابع")
        self.assertIsNone(copied_value.value)
        self.assertEqual(copied_item.status, ResultStatus.UNCHECKED)
        self.assertEqual(copied_item.observation, "")
        self.assertEqual(copied_child.scope_origin, ScopeOrigin.LOCAL)
        self.assertNotEqual(copied_child.id, child.id)

        copied_ids = [
            (ProposalType.NODE, clone.id),
            (ProposalType.SPECIFICATION, copied_value.id),
            (ProposalType.ITEM, copied_item.id),
            (ProposalType.NODE, copied_child.id),
        ]
        for proposal_type, local_id in copied_ids:
            self.assertTrue(
                Proposal.objects.filter(
                    proposal_type=proposal_type,
                    source_local_id=local_id,
                    status=ProposalStatus.PENDING,
                ).exists()
            )

    def test_local_node_cannot_move_inside_its_own_subtree(self):
        parent = self.local_node(title="أب محلي")
        child = self.local_node(parent, title="ابن محلي")

        with self.assertRaises(ValidationError):
            move_local_node(parent, child, self.inspector)

        parent.refresh_from_db()
        self.assertEqual(parent.parent_id, self.snap_root.id)

    def test_reference_content_cannot_be_edited_directly(self):
        reference_item = self.snap_root.item_results.get(source_item=self.root_item)
        with self.assertRaises(ValidationError):
            update_local_item(
                reference_item,
                self.inspector,
                {"title": "تعديل غير مسموح", "guidance": ""},
            )

    def test_admin_cannot_edit_inspector_local_content(self):
        item = self.local_item()
        self.client.login(username="authoring-admin", password="test-pass-123")
        response = self.client.get(
            reverse("local_item_edit", args=[self.inspection.pk, item.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_completed_visit_rejects_local_editing(self):
        item = self.local_item()
        self.inspection.status = InspectionStatus.COMPLETED
        self.inspection.save(update_fields=["status"])

        self.client.login(username="authoring-inspector", password="test-pass-123")
        response = self.client.get(
            reverse("local_item_edit", args=[self.inspection.pk, item.pk])
        )
        self.assertEqual(response.status_code, 403)


    def test_restore_local_item_reactivates_pruned_context_path(self):
        context_source = StructureNode.objects.create(
            master_version=self.master,
            title="سياق منفرد",
            sort_order=80,
        )
        context = InspectionNode.objects.create(
            inspection=self.inspection,
            source_node=context_source,
            title_snapshot=context_source.title,
            sort_order_snapshot=80,
            scope_origin=ScopeOrigin.MANUAL,
            scope_state=ScopeState.ACTIVE,
            scope_role=ScopeRole.CONTEXT,
        )
        item = self.local_item(context, title="بند داخل سياق")
        remove_local_item(item, self.inspector)

        context.refresh_from_db()
        self.assertEqual(context.scope_state, ScopeState.EXCLUDED)

        restore_local_item(item, self.inspector)
        context.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(context.scope_state, ScopeState.ACTIVE)
        self.assertEqual(item.scope_state, ScopeState.ACTIVE)
