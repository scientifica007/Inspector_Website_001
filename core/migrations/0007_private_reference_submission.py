from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_inspectable_snapshot(apps, schema_editor):
    InspectionNode = apps.get_model("core", "InspectionNode")
    Proposal = apps.get_model("core", "Proposal")

    for node in InspectionNode.objects.select_related("source_node").all():
        value = True
        if node.source_node_id:
            value = bool(node.source_node.inspectable)
        elif node.scope_origin == "LOCAL":
            proposal = (
                Proposal.objects.filter(
                    source_inspection_id=node.inspection_id,
                    proposal_type="NODE",
                    source_local_id=node.id,
                )
                .order_by("-id")
                .first()
            )
            if proposal:
                value = bool((proposal.payload or {}).get("inspectable", True))
        node.inspectable_snapshot = value
        node.save(update_fields=["inspectable_snapshot"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_reference_library_core"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="inspectionnode",
            name="inspectable_snapshot",
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name="ReferenceSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_name_snapshot", models.CharField(max_length=255)),
                ("snapshot", models.JSONField(default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "قيد المراجعة"),
                            ("APPROVED", "معتمد"),
                            ("REJECTED", "مرفوض"),
                            ("WITHDRAWN", "مسحوب"),
                        ],
                        default="PENDING",
                        max_length=16,
                    ),
                ),
                ("resolution_note", models.TextField(blank=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "resolved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reference_submissions_resolved",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "resulting_reference",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="originating_submissions",
                        to="core.masterversion",
                    ),
                ),
                (
                    "source_reference",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="submissions",
                        to="core.masterversion",
                    ),
                ),
                (
                    "submitted_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reference_submissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.RunPython(backfill_inspectable_snapshot, migrations.RunPython.noop),
    ]
