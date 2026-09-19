from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class FreezeInspectionReferenceMigrationTests(TransactionTestCase):
    migrate_from = ("core", "0007_private_reference_submission")
    migrate_to = ("core", "0008_freeze_inspection_reference")

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

        user = User.objects.create(username="freeze-migration")
        institution = Institution.objects.create(name="مؤسسة تجميد")
        source = MasterVersion.objects.create(
            number=1,
            name="مرجع قبل التجميد",
            visibility="SHARED",
            status="PUBLISHED",
        )
        root = StructureNode.objects.create(
            master_version=source,
            title="المجال",
            inspectable=False,
        )
        spec = SpecificationDefinition.objects.create(
            node=root,
            title="عدد العمال",
            field_type="NUMBER",
        )
        item = ChecklistItem.objects.create(
            node=root,
            title="سلامة التنظيم",
        )
        inspection = Inspection.objects.create(
            institution=institution,
            inspector=user,
            master_version=source,
            reference_name_snapshot=source.name,
            visit_date="2026-09-19",
        )
        snap = InspectionNode.objects.create(
            inspection=inspection,
            source_node=root,
            title_snapshot=root.title,
            inspectable_snapshot=False,
        )
        value = SpecificationValue.objects.create(
            inspection_node=snap,
            source_specification=spec,
            title_snapshot=spec.title,
            field_type_snapshot=spec.field_type,
        )
        result = InspectionItemResult.objects.create(
            inspection_node=snap,
            source_item=item,
            title_snapshot=item.title,
        )

        self.source_id = source.id
        self.source_node_id = root.id
        self.source_spec_id = spec.id
        self.source_item_id = item.id
        self.inspection_id = inspection.id
        self.snap_id = snap.id
        self.value_id = value.id
        self.result_id = result.id
        self.node_stable = str(root.stable_id)
        self.spec_stable = str(spec.stable_id)
        self.item_stable = str(item.stable_id)

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_existing_inspection_gets_private_internal_reference_snapshot_and_rewired_sources(self):
        MasterVersion = self.apps.get_model("core", "MasterVersion")
        Inspection = self.apps.get_model("core", "Inspection")
        InspectionNode = self.apps.get_model("core", "InspectionNode")
        SpecificationValue = self.apps.get_model("core", "SpecificationValue")
        InspectionItemResult = self.apps.get_model("core", "InspectionItemResult")

        inspection = Inspection.objects.get(pk=self.inspection_id)
        self.assertEqual(inspection.source_reference_id, self.source_id)
        self.assertNotEqual(inspection.master_version_id, self.source_id)

        frozen = MasterVersion.objects.get(pk=inspection.master_version_id)
        self.assertEqual(frozen.visibility, "SNAPSHOT")
        self.assertEqual(frozen.name, "مرجع قبل التجميد")

        snap = InspectionNode.objects.get(pk=self.snap_id)
        value = SpecificationValue.objects.get(pk=self.value_id)
        result = InspectionItemResult.objects.get(pk=self.result_id)

        self.assertNotEqual(snap.source_node_id, self.source_node_id)
        self.assertNotEqual(value.source_specification_id, self.source_spec_id)
        self.assertNotEqual(result.source_item_id, self.source_item_id)
        self.assertEqual(str(snap.source_node.stable_id), self.node_stable)
        self.assertEqual(
            str(value.source_specification.stable_id),
            self.spec_stable,
        )
        self.assertEqual(str(result.source_item.stable_id), self.item_stable)

    def test_deleting_original_reference_after_migration_keeps_internal_snapshot(self):
        MasterVersion = self.apps.get_model("core", "MasterVersion")
        Inspection = self.apps.get_model("core", "Inspection")

        inspection = Inspection.objects.get(pk=self.inspection_id)
        frozen_id = inspection.master_version_id
        MasterVersion.objects.get(pk=self.source_id).delete()

        inspection.refresh_from_db()
        self.assertIsNone(inspection.source_reference_id)
        self.assertEqual(inspection.master_version_id, frozen_id)
        self.assertTrue(
            MasterVersion.objects.filter(
                pk=frozen_id,
                visibility="SNAPSHOT",
            ).exists()
        )
