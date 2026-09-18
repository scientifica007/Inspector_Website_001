from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class SelectiveScopeMigrationTests(TransactionTestCase):
    migrate_from = ("core", "0003_governance_stable_ids")
    migrate_to = ("core", "0004_selective_visit_scope")

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

        user = User.objects.create(username="migration-inspector")
        institution = Institution.objects.create(name="مؤسسة تاريخية")
        master = MasterVersion.objects.create(number=1, status="PUBLISHED")
        source = StructureNode.objects.create(
            master_version=master,
            title="مجال تاريخي",
        )
        source_spec = SpecificationDefinition.objects.create(
            node=source,
            title="مواصفة تاريخية",
            field_type="SHORT_TEXT",
        )
        source_item = ChecklistItem.objects.create(
            node=source,
            title="بند تاريخي",
        )
        inspection = Inspection.objects.create(
            institution=institution,
            inspector=user,
            master_version=master,
            visit_date="2026-09-18",
        )
        legacy_node = InspectionNode.objects.create(
            inspection=inspection,
            source_node=source,
            title_snapshot="مجال تاريخي",
            local_addition=False,
        )
        local_node = InspectionNode.objects.create(
            inspection=inspection,
            parent=legacy_node,
            title_snapshot="فرع محلي",
            local_addition=True,
        )
        SpecificationValue.objects.create(
            inspection_node=legacy_node,
            source_specification=source_spec,
            title_snapshot="مواصفة تاريخية",
            field_type_snapshot="SHORT_TEXT",
            value="قيمة محفوظة",
            local_addition=False,
        )
        InspectionItemResult.objects.create(
            inspection_node=legacy_node,
            source_item=source_item,
            title_snapshot="بند تاريخي",
            status="OBSERVATION",
            observation="ملاحظة محفوظة",
            local_addition=False,
        )
        InspectionItemResult.objects.create(
            inspection_node=local_node,
            title_snapshot="بند محلي",
            observation="بيانات محلية محفوظة",
            local_addition=True,
        )

        self.inspection_id = inspection.id
        self.legacy_node_id = legacy_node.id
        self.local_node_id = local_node.id

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_existing_snapshots_are_classified_without_data_loss(self):
        Inspection = self.apps.get_model("core", "Inspection")
        InspectionNode = self.apps.get_model("core", "InspectionNode")
        SpecificationValue = self.apps.get_model("core", "SpecificationValue")
        InspectionItemResult = self.apps.get_model("core", "InspectionItemResult")

        inspection = Inspection.objects.get(pk=self.inspection_id)
        legacy_node = InspectionNode.objects.get(pk=self.legacy_node_id)
        local_node = InspectionNode.objects.get(pk=self.local_node_id)

        self.assertEqual(inspection.scope_mode, "LEGACY_FULL")
        self.assertEqual(legacy_node.scope_origin, "LEGACY")
        self.assertEqual(legacy_node.scope_state, "ACTIVE")
        self.assertEqual(legacy_node.scope_role, "SELECTED")
        self.assertEqual(local_node.scope_origin, "LOCAL")

        spec = SpecificationValue.objects.get(inspection_node=legacy_node)
        self.assertEqual(spec.scope_origin, "LEGACY")
        self.assertEqual(spec.value, "قيمة محفوظة")

        historical_item = InspectionItemResult.objects.get(
            inspection_node=legacy_node
        )
        self.assertEqual(historical_item.scope_origin, "LEGACY")
        self.assertEqual(historical_item.status, "OBSERVATION")
        self.assertEqual(historical_item.observation, "ملاحظة محفوظة")

        local_item = InspectionItemResult.objects.get(inspection_node=local_node)
        self.assertEqual(local_item.scope_origin, "LOCAL")
        self.assertEqual(local_item.observation, "بيانات محلية محفوظة")
