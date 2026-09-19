from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def preserve_existing_constraint_baseline(apps, schema_editor):
    InspectionNode = apps.get_model("core", "InspectionNode")
    SpecificationValue = apps.get_model("core", "SpecificationValue")
    InspectionItemResult = apps.get_model("core", "InspectionItemResult")

    InspectionNode.objects.filter(scope_locked=True).update(base_scope_locked=True)
    SpecificationValue.objects.filter(scope_locked=True).update(base_scope_locked=True)
    SpecificationValue.objects.filter(completion_required=True).update(
        base_completion_required=True
    )
    InspectionItemResult.objects.filter(scope_locked=True).update(base_scope_locked=True)
    InspectionItemResult.objects.filter(completion_required=True).update(
        base_completion_required=True
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0009_guides"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="inspectionnode",
            name="base_scope_locked",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="specificationvalue",
            name="base_scope_locked",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="specificationvalue",
            name="base_completion_required",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="inspectionitemresult",
            name="base_scope_locked",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="inspectionitemresult",
            name="base_completion_required",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="Assignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "مسودة تكليف"),
                            ("ISSUED", "صادر"),
                            ("REVOKED", "ملغى"),
                        ],
                        default="DRAFT",
                        max_length=16,
                    ),
                ),
                ("issued_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("revocation_reason", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assignments_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "inspection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignments",
                        to="core.inspection",
                    ),
                ),
                (
                    "issued_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assignments_issued",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "revoked_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assignments_revoked",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.CreateModel(
            name="AssignmentEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "entry_type",
                    models.CharField(
                        choices=[
                            ("BRANCH", "فرع كامل"),
                            ("SPECIFICATION", "وصف"),
                            ("ITEM", "بند"),
                        ],
                        max_length=20,
                    ),
                ),
                ("stable_id", models.UUIDField()),
                ("label_snapshot", models.CharField(max_length=500)),
                ("scope_locked", models.BooleanField(default=False)),
                ("completion_required", models.BooleanField(default=False)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                (
                    "assignment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entries",
                        to="core.assignment",
                    ),
                ),
            ],
            options={"ordering": ["sort_order", "id"]},
        ),
        migrations.CreateModel(
            name="AssignmentEffect",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scope_locked", models.BooleanField(default=False)),
                ("completion_required", models.BooleanField(default=False)),
                (
                    "assignment_entry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="effects",
                        to="core.assignmententry",
                    ),
                ),
                (
                    "item",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignment_effects",
                        to="core.inspectionitemresult",
                    ),
                ),
                (
                    "node",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignment_effects",
                        to="core.inspectionnode",
                    ),
                ),
                (
                    "specification",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignment_effects",
                        to="core.specificationvalue",
                    ),
                ),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.RunPython(
            preserve_existing_constraint_baseline,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="assignmententry",
            constraint=models.UniqueConstraint(
                fields=("assignment", "entry_type", "stable_id"),
                name="uq_assignment_entry_target",
            ),
        ),
        migrations.AddConstraint(
            model_name="assignmententry",
            constraint=models.CheckConstraint(
                condition=models.Q(("scope_locked", True), ("completion_required", True), _connector="OR"),
                name="ck_assignment_entry_has_obligation",
            ),
        ),
        migrations.AddConstraint(
            model_name="assignmenteffect",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(("node__isnull", False), ("specification__isnull", True), ("item__isnull", True))
                    | models.Q(("node__isnull", True), ("specification__isnull", False), ("item__isnull", True))
                    | models.Q(("node__isnull", True), ("specification__isnull", True), ("item__isnull", False))
                ),
                name="ck_assignment_effect_one_target",
            ),
        ),
        migrations.AddConstraint(
            model_name="assignmenteffect",
            constraint=models.UniqueConstraint(
                condition=models.Q(("node__isnull", False)),
                fields=("assignment_entry", "node"),
                name="uq_assignment_effect_node",
            ),
        ),
        migrations.AddConstraint(
            model_name="assignmenteffect",
            constraint=models.UniqueConstraint(
                condition=models.Q(("specification__isnull", False)),
                fields=("assignment_entry", "specification"),
                name="uq_assignment_effect_spec",
            ),
        ),
        migrations.AddConstraint(
            model_name="assignmenteffect",
            constraint=models.UniqueConstraint(
                condition=models.Q(("item__isnull", False)),
                fields=("assignment_entry", "item"),
                name="uq_assignment_effect_item",
            ),
        ),
    ]
