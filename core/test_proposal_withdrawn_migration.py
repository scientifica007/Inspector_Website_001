from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ProposalWithdrawnMigrationTests(TransactionTestCase):
    migrate_from = ("core", "0004_selective_visit_scope")
    migrate_to = ("core", "0005_proposal_withdrawn")

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps

        User = old_apps.get_model("auth", "User")
        Institution = old_apps.get_model("core", "Institution")
        MasterVersion = old_apps.get_model("core", "MasterVersion")
        Inspection = old_apps.get_model("core", "Inspection")
        Proposal = old_apps.get_model("core", "Proposal")

        user = User.objects.create(username="withdrawn-migration")
        institution = Institution.objects.create(name="مؤسسة ترحيل")
        master = MasterVersion.objects.create(number=1, status="PUBLISHED")
        inspection = Inspection.objects.create(
            institution=institution,
            inspector=user,
            master_version=master,
            visit_date="2026-09-18",
        )
        self.ids = []
        for index, status in enumerate(("PENDING", "APPROVED", "REJECTED", "MERGED"), start=1):
            proposal = Proposal.objects.create(
                proposal_type="ITEM",
                source_inspection=inspection,
                source_local_id=index,
                proposed_by=user,
                payload={"title": f"بند {index}"},
                status=status,
            )
            self.ids.append((proposal.id, status))

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_existing_proposal_statuses_are_unchanged_and_withdrawn_is_available(self):
        Proposal = self.apps.get_model("core", "Proposal")
        for proposal_id, status in self.ids:
            self.assertEqual(Proposal.objects.get(pk=proposal_id).status, status)

        status_field = Proposal._meta.get_field("status")
        choices = dict(status_field.choices)
        self.assertEqual(choices["WITHDRAWN"], "مسحوب")

        type_field = Proposal._meta.get_field("proposal_type")
        self.assertEqual(dict(type_field.choices)["SPECIFICATION"], "وصف")
