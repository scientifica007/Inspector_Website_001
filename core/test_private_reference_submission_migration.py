from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class PrivateReferenceSubmissionMigrationTests(TransactionTestCase):
    migrate_from = ("core", "0006_reference_library_core")
    migrate_to = ("core", "0007_private_reference_submission")

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps

        User = old_apps.get_model("auth", "User")
        Institution = old_apps.get_model("core", "Institution")
        MasterVersion = old_apps.get_model("core", "MasterVersion")
        StructureNode = old_apps.get_model("core", "StructureNode")
        Inspection = old_apps.get_model("core", "Inspection")
        InspectionNode = old_apps.get_model("core", "InspectionNode")
        Proposal = old_apps.get_model("core", "Proposal")

        user = User.objects.create(username="submission-migration")
        institution = Institution.objects.create(name="مؤسسة ترحيل")
        reference = MasterVersion.objects.create(
            number=1,
            name="مرجع ترحيل",
            visibility="SHARED",
            status="PUBLISHED",
        )
        source = StructureNode.objects.create(
            master_version=reference,
            title="مرجعي",
            inspectable=False,
        )
        inspection = Inspection.objects.create(
            institution=institution,
            inspector=user,
            master_version=reference,
            reference_name_snapshot=reference.name,
            visit_date="2026-09-19",
        )
        reference_node = InspectionNode.objects.create(
            inspection=inspection,
            source_node=source,
            title_snapshot="مرجعي",
            scope_origin="MANUAL",
        )
        local_node = InspectionNode.objects.create(
            inspection=inspection,
            title_snapshot="محلي",
            scope_origin="LOCAL",
        )
        Proposal.objects.create(
            proposal_type="NODE",
            source_inspection=inspection,
            source_local_id=local_node.id,
            proposed_by=user,
            payload={"inspectable": False, "title": "محلي", "target_root": True},
        )
        self.reference_node_id = reference_node.id
        self.local_node_id = local_node.id

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_inspectable_snapshot_is_backfilled_from_reference_or_legacy_proposal(self):
        InspectionNode = self.apps.get_model("core", "InspectionNode")
        reference_node = InspectionNode.objects.get(pk=self.reference_node_id)
        local_node = InspectionNode.objects.get(pk=self.local_node_id)
        self.assertFalse(reference_node.inspectable_snapshot)
        self.assertFalse(local_node.inspectable_snapshot)

    def test_reference_submission_model_has_required_statuses(self):
        ReferenceSubmission = self.apps.get_model("core", "ReferenceSubmission")
        choices = dict(ReferenceSubmission._meta.get_field("status").choices)
        self.assertEqual(choices["PENDING"], "قيد المراجعة")
        self.assertEqual(choices["APPROVED"], "معتمد")
        self.assertEqual(choices["REJECTED"], "مرفوض")
        self.assertEqual(choices["WITHDRAWN"], "مسحوب")
