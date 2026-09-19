from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class GuideMigrationTests(TransactionTestCase):
    migrate_from = ("core", "0008_freeze_inspection_reference")
    migrate_to = ("core", "0009_guides")

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps

        User = old_apps.get_model("auth", "User")
        Institution = old_apps.get_model("core", "Institution")
        MasterVersion = old_apps.get_model("core", "MasterVersion")
        Inspection = old_apps.get_model("core", "Inspection")

        user = User.objects.create(username="guide-migration")
        institution = Institution.objects.create(name="مؤسسة قبل الأدلة")
        reference = MasterVersion.objects.create(
            number=1,
            name="مرجع قبل الأدلة",
            visibility="SHARED",
            status="PUBLISHED",
        )
        inspection = Inspection.objects.create(
            institution=institution,
            inspector=user,
            master_version=reference,
            source_reference=reference,
            reference_name_snapshot=reference.name,
            visit_date="2026-09-19",
        )
        self.inspection_id = inspection.id
        self.before = {
            "master_version_id": inspection.master_version_id,
            "source_reference_id": inspection.source_reference_id,
            "reference_name_snapshot": inspection.reference_name_snapshot,
            "status": inspection.status,
            "scope_mode": inspection.scope_mode,
        }

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_guide_migration_is_additive_and_does_not_rewrite_inspection(self):
        Inspection = self.apps.get_model("core", "Inspection")
        Guide = self.apps.get_model("core", "Guide")
        GuideEntry = self.apps.get_model("core", "GuideEntry")
        GuideApplication = self.apps.get_model("core", "GuideApplication")

        inspection = Inspection.objects.get(pk=self.inspection_id)
        after = {
            "master_version_id": inspection.master_version_id,
            "source_reference_id": inspection.source_reference_id,
            "reference_name_snapshot": inspection.reference_name_snapshot,
            "status": inspection.status,
            "scope_mode": inspection.scope_mode,
        }

        self.assertEqual(after, self.before)
        self.assertEqual(Guide.objects.count(), 0)
        self.assertEqual(GuideEntry.objects.count(), 0)
        self.assertEqual(GuideApplication.objects.count(), 0)
