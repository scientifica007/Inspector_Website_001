from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_freeze_inspection_reference"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Guide",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="guides_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reference",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="guides",
                        to="core.masterversion",
                    ),
                ),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.CreateModel(
            name="GuideEntry",
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
                ("sort_order", models.PositiveIntegerField(default=0)),
                (
                    "guide",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entries",
                        to="core.guide",
                    ),
                ),
            ],
            options={"ordering": ["sort_order", "id"]},
        ),
        migrations.CreateModel(
            name="GuideApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("guide_name_snapshot", models.CharField(max_length=255)),
                ("guide_snapshot", models.JSONField(default=dict)),
                ("applied_count", models.PositiveIntegerField(default=0)),
                ("skipped_count", models.PositiveIntegerField(default=0)),
                ("result_details", models.JSONField(blank=True, default=list)),
                ("applied_at", models.DateTimeField(auto_now_add=True)),
                (
                    "applied_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="guide_applications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "guide",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="applications",
                        to="core.guide",
                    ),
                ),
                (
                    "inspection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="guide_applications",
                        to="core.inspection",
                    ),
                ),
            ],
            options={"ordering": ["-applied_at", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="guideentry",
            constraint=models.UniqueConstraint(
                fields=("guide", "entry_type", "stable_id"),
                name="uq_guide_entry_target",
            ),
        ),
        migrations.AddConstraint(
            model_name="guideapplication",
            constraint=models.UniqueConstraint(
                condition=models.Q(("guide__isnull", False)),
                fields=("inspection", "guide"),
                name="uq_inspection_guide_application",
            ),
        ),
    ]
