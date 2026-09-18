from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .builder_forms import SpecificationDefinitionForm, StructureNodeForm
from .models import (
    ChecklistItem,
    FieldType,
    MasterStatus,
    MasterVersion,
    SpecificationDefinition,
    StructureNode,
)
from .services import create_draft_from_latest_published, flatten_nodes

User = get_user_model()

class AdminBuilderTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            "admin-builder", "admin@example.com", "test-pass-123"
        )
        self.inspector = User.objects.create_user(
            "inspector-builder", password="test-pass-123"
        )

    def login_admin(self):
        self.client.login(username="admin-builder", password="test-pass-123")

    def test_builder_is_admin_only(self):
        self.client.login(username="inspector-builder", password="test-pass-123")
        response = self.client.get(reverse("builder_home"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_open_builder(self):
        self.login_admin()
        response = self.client.get(reverse("builder_home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "هندسة مرجع التفتيش")

    def test_draft_clone_preserves_tree_specs_and_items(self):
        published = MasterVersion.objects.create(number=1, status=MasterStatus.PUBLISHED)
        root = StructureNode.objects.create(
            master_version=published, title="المجال", sort_order=1
        )
        child = StructureNode.objects.create(
            master_version=published, parent=root, title="المصلحة", sort_order=2
        )
        SpecificationDefinition.objects.create(
            node=root,
            title="عدد الموظفين",
            field_type=FieldType.NUMBER,
            required=True,
            sort_order=1,
        )
        ChecklistItem.objects.create(
            node=child, title="توفر برنامج عمل", guidance="تحقق من الوثيقة", sort_order=1
        )

        draft, created = create_draft_from_latest_published()
        self.assertTrue(created)
        self.assertEqual(draft.number, 2)
        cloned_root = draft.nodes.get(title="المجال")
        cloned_child = draft.nodes.get(title="المصلحة")
        self.assertEqual(cloned_child.parent, cloned_root)
        self.assertTrue(cloned_root.specifications.get().required)
        self.assertEqual(cloned_child.items.get().guidance, "تحقق من الوثيقة")

        same, created_again = create_draft_from_latest_published()
        self.assertFalse(created_again)
        self.assertEqual(same, draft)

    def test_node_form_blocks_cross_version_parent(self):
        draft = MasterVersion.objects.create(number=2, status=MasterStatus.DRAFT)
        other = MasterVersion.objects.create(number=1, status=MasterStatus.PUBLISHED)
        foreign_parent = StructureNode.objects.create(master_version=other, title="خارج المسودة")
        form = StructureNodeForm(
            data={
                "title": "عنصر",
                "description": "",
                "inspectable": "on",
                "parent": foreign_parent.pk,
                "sort_order": 0,
                "active": "on",
            },
            draft=draft,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("parent", form.errors)

    def test_node_form_blocks_recursive_cycle(self):
        draft = MasterVersion.objects.create(number=1, status=MasterStatus.DRAFT)
        root = StructureNode.objects.create(master_version=draft, title="جذر")
        child = StructureNode.objects.create(master_version=draft, parent=root, title="فرع")
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
            draft=draft,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("parent", form.errors)

    def test_admin_can_create_child_node(self):
        draft = MasterVersion.objects.create(number=1, status=MasterStatus.DRAFT)
        parent = StructureNode.objects.create(master_version=draft, title="مديرية فرعية")
        self.login_admin()
        response = self.client.post(
            reverse("builder_node_create"),
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
        self.assertEqual(child.master_version, draft)

    def test_select_specification_requires_options_and_parses_lines(self):
        draft = MasterVersion.objects.create(number=1, status=MasterStatus.DRAFT)
        node = StructureNode.objects.create(master_version=draft, title="مجال")
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

    def test_published_node_cannot_be_edited_through_builder(self):
        published = MasterVersion.objects.create(number=1, status=MasterStatus.PUBLISHED)
        node = StructureNode.objects.create(master_version=published, title="منشور")
        self.login_admin()
        response = self.client.get(reverse("builder_node_edit", args=[node.pk]))
        self.assertEqual(response.status_code, 404)

    def test_inactive_branch_is_hidden_from_preview_tree(self):
        draft = MasterVersion.objects.create(number=1, status=MasterStatus.DRAFT)
        hidden = StructureNode.objects.create(
            master_version=draft, title="فرع معطل", active=False
        )
        StructureNode.objects.create(
            master_version=draft, parent=hidden, title="ابن نشط", active=True
        )
        StructureNode.objects.create(
            master_version=draft, title="فرع ظاهر", active=True
        )
        titles = [node.title for node, _ in flatten_nodes(draft, active_only=True)]
        self.assertEqual(titles, ["فرع ظاهر"])

    def test_preview_does_not_publish_or_mutate_draft(self):
        draft = MasterVersion.objects.create(number=1, status=MasterStatus.DRAFT)
        StructureNode.objects.create(master_version=draft, title="التجهيزات")
        self.login_admin()
        response = self.client.get(reverse("builder_preview"))
        self.assertEqual(response.status_code, 200)
        draft.refresh_from_db()
        self.assertEqual(draft.status, MasterStatus.DRAFT)
