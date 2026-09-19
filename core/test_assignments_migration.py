from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class AssignmentMigrationTests(TransactionTestCase):
    migrate_from = ("core", "0009_guides")
    migrate_to = ("core", "0010_assignments")

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps

        User = old_apps.get_model("auth", "User")
        Institution = old_apps.get_model("core", "Institution")
        MasterVersion = old_apps.get_model("core", "MasterVersion")
        StructureNode = old_apps.get_model("core", "StructureNode")
        SpecificationDefinition = old_apps.get_model("core", "SpecificationDefinition")
        ChecklistItem = old_apps.get_model("core", "ChecklistItem")
        Inspection = old_apps.get_model("core", "Inspection")
        InspectionNode = old_apps.get_model("core", "InspectionNode")
        SpecificationValue = old_apps.get_model("core", "SpecificationValue")
        InspectionItemResult = old_apps.get_model("core", "InspectionItemResult")

        user = User.objects.create(username="assignment-migration")
        institution = Institution.objects.create(name="مؤسسة ترحيل التكليف")
        reference = MasterVersion.objects.create(
            number=1,
            name="مرجع ترحيل التكليف",
            visibility="SNAPSHOT",
            status="DRAFT",
        )
        source_node = StructureNode.objects.create(
            master_version=reference,
            title="مجال",
        )
        source_spec = SpecificationDefinition.objects.create(
            node=source_node,
            title="وصف",
            field_type="SHORT_TEXT",
        )
        source_item = ChecklistItem.objects.create(
            node=source_node,
            title="بند",
        )
        inspection = Inspection.objects.create(
            institution=institution,
            inspector=user,
            master_version=reference,
            reference_name_snapshot="مرجع",
            visit_date="2026-09-19",
        )
        node = InspectionNode.objects.create(
            inspection=inspection,
            source_node=source_node,
            title_snapshot="مجال",
            scope_locked=True,
        )
        spec = SpecificationValue.objects.create(
            inspection_node=node,
            source_specification=source_spec,
            title_snapshot="وصف",
            field_type_snapshot="SHORT_TEXT",
            scope_locked=True,
            completion_required=True,
        )
        item = InspectionItemResult.objects.create(
            inspection_node=node,
            source_item=source_item,
            title_snapshot="بند",
            scope_locked=True,
            completion_required=True,
        )

        self.inspection_id = inspection.id
        self.node_id = node.id
        self.spec_id = spec.id
        self.item_id = item.id

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_existing_constraints_become_baseline_without_data_rewrite(self):
        Inspection = self.apps.get_model("core", "Inspection")
        InspectionNode = self.apps.get_model("core", "InspectionNode")
        SpecificationValue = self.apps.get_model("core", "SpecificationValue")
        InspectionItemResult = self.apps.get_model("core", "InspectionItemResult")
        Assignment = self.apps.get_model("core", "Assignment")
        AssignmentEffect = self.apps.get_model("core", "AssignmentEffect")

        inspection = Inspection.objects.get(pk=self.inspection_id)
        node = InspectionNode.objects.get(pk=self.node_id)
        spec = SpecificationValue.objects.get(pk=self.spec_id)
        item = InspectionItemResult.objects.get(pk=self.item_id)

        self.assertEqual(inspection.status, "DRAFT")
        self.assertTrue(node.scope_locked)
        self.assertTrue(node.base_scope_locked)
        self.assertTrue(spec.scope_locked)
        self.assertTrue(spec.base_scope_locked)
        self.assertTrue(spec.completion_required)
        self.assertTrue(spec.base_completion_required)
        self.assertTrue(item.scope_locked)
        self.assertTrue(item.base_scope_locked)
        self.assertTrue(item.completion_required)
        self.assertTrue(item.base_completion_required)
        self.assertEqual(Assignment.objects.count(), 0)
        self.assertEqual(AssignmentEffect.objects.count(), 0)
