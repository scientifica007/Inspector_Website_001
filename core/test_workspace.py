from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    FieldType,
    Inspection,
    Institution,
    MasterStatus,
    MasterVersion,
    ScopeOrigin,
    ScopeRole,
    SpecificationValue,
    StructureNode,
)


User = get_user_model()


class WorkspaceSeparationTests(TestCase):
    def setUp(self):
        self.inspector = User.objects.create_user("workspace-inspector", password="test-pass-123")
        self.admin = User.objects.create_superuser("workspace-admin", "admin@example.com", "test-pass-123")
        self.institution = Institution.objects.create(name="مؤسسة مساحة العمل")
        self.master = MasterVersion.objects.create(number=1, status=MasterStatus.PUBLISHED)
        self.inspection = Inspection.objects.create(
            institution=self.institution,
            inspector=self.inspector,
            master_version=self.master,
            visit_date=date(2026, 9, 18),
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
            sort_order=10,
        )
        self.root_snapshot = self.inspection.inspection_nodes.create(
            source_node=self.root,
            title_snapshot=self.root.title,
            sort_order_snapshot=10,
            scope_origin=ScopeOrigin.MANUAL,
            scope_role=ScopeRole.SELECTED,
        )
        self.child_snapshot = self.inspection.inspection_nodes.create(
            source_node=self.child,
            parent=self.root_snapshot,
            title_snapshot=self.child.title,
            sort_order_snapshot=10,
            scope_origin=ScopeOrigin.MANUAL,
            scope_role=ScopeRole.SELECTED,
        )
        self.description = SpecificationValue.objects.create(
            inspection_node=self.child_snapshot,
            title_snapshot="اسم المسؤول",
            field_type_snapshot=FieldType.SHORT_TEXT,
            required_snapshot=True,
            scope_origin=ScopeOrigin.LOCAL,
        )

    def test_home_is_general_workspace_not_visit_list(self):
        self.client.login(username="workspace-inspector", password="test-pass-123")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "الرئيسية")
        self.assertContains(response, "زياراتي")
        self.assertContains(response, "المؤسسات")
        self.assertNotContains(response, self.institution.name)

    def test_admin_visit_list_is_named_visits_not_my_visits(self):
        self.client.login(username="workspace-admin", password="test-pass-123")
        response = self.client.get(reverse("inspection_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "الزيارات")
        self.assertNotContains(response, "زياراتي")
        self.assertContains(response, self.institution.name)

    def test_preparation_does_not_render_required_value_input(self):
        self.client.login(username="workspace-inspector", password="test-pass-123")
        response = self.client.get(
            reverse("inspection_node_prepare", args=[self.inspection.pk, self.child_snapshot.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "إلزامي عند التنفيذ")
        self.assertNotContains(response, f'name="spec_{self.description.id}"')
        self.assertContains(
            response,
            reverse("inspection_node_prepare", args=[self.inspection.pk, self.root_snapshot.pk]),
        )

    def test_execution_renders_value_input_and_keeps_authoring_out(self):
        self.client.login(username="workspace-inspector", password="test-pass-123")
        response = self.client.get(
            reverse("inspection_node", args=[self.inspection.pk, self.child_snapshot.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'name="spec_{self.description.id}"')
        self.assertContains(response, "تنفيذ الزيارة")
        self.assertNotContains(response, "+ وصف")

    def test_overview_links_to_prepare_and_execute(self):
        self.client.login(username="workspace-inspector", password="test-pass-123")
        response = self.client.get(reverse("inspection_detail", args=[self.inspection.pk]))
        self.assertContains(response, reverse("inspection_prepare", args=[self.inspection.pk]))
        self.assertContains(response, reverse("inspection_execute", args=[self.inspection.pk]))
