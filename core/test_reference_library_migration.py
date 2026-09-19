from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ReferenceLibraryMigrationTests(TransactionTestCase):
    migrate_from = ("core", "0005_proposal_withdrawn")
    migrate_to = ("core", "0006_reference_library_core")

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps

        User = old_apps.get_model("auth", "User")
        Institution = old_apps.get_model("core", "Institution")
        MasterVersion = old_apps.get_model("core", "MasterVersion")
        Inspection = old_apps.get_model("core", "Inspection")

        user = User.objects.create(username="reference-migration")
        institution = Institution.objects.create(name="مؤسسة ترحيل المراجع")

        published = MasterVersion.objects.create(number=1, status="PUBLISHED")
        draft = MasterVersion.objects.create(number=2, status="DRAFT")
        archived = MasterVersion.objects.create(number=3, status="ARCHIVED")

        self.reference_ids = {
            "published": published.id,
            "draft": draft.id,
            "archived": archived.id,
        }
        inspection = Inspection.objects.create(
            institution=institution,
            inspector=user,
            master_version=published,
            visit_date="2026-09-19",
        )
        self.inspection_id = inspection.id

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_existing_versions_become_independent_reference_metadata_without_visit_loss(self):
        MasterVersion = self.apps.get_model("core", "MasterVersion")
        Inspection = self.apps.get_model("core", "Inspection")

        published = MasterVersion.objects.get(pk=self.reference_ids["published"])
        draft = MasterVersion.objects.get(pk=self.reference_ids["draft"])
        archived = MasterVersion.objects.get(pk=self.reference_ids["archived"])
        inspection = Inspection.objects.get(pk=self.inspection_id)

        self.assertEqual(published.visibility, "SHARED")
        self.assertEqual(published.name, "مرجع التفتيش العام")
        self.assertEqual(draft.visibility, "PRIVATE")
        self.assertTrue(draft.name.startswith("مرجع إداري قيد العمل"))
        self.assertEqual(archived.visibility, "PRIVATE")
        self.assertTrue(archived.name.startswith("مرجع إداري سابق"))
        self.assertEqual(
            inspection.reference_name_snapshot,
            published.name,
        )

        published.delete()
        inspection.refresh_from_db()
        self.assertIsNone(inspection.master_version_id)
        self.assertEqual(
            inspection.reference_name_snapshot,
            "مرجع التفتيش العام",
        )
