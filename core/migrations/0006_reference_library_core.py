from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def classify_existing_references(apps, schema_editor):
    MasterVersion = apps.get_model("core", "MasterVersion")
    Inspection = apps.get_model("core", "Inspection")

    for reference in MasterVersion.objects.all().order_by("number", "id"):
        if reference.status == "PUBLISHED":
            name = "مرجع التفتيش العام" if reference.number == 1 else f"مرجع التفتيش العام {reference.number}"
            visibility = "SHARED"
        elif reference.status == "DRAFT":
            name = f"مرجع إداري قيد العمل {reference.number}"
            visibility = "PRIVATE"
        else:
            name = f"مرجع إداري سابق {reference.number}"
            visibility = "PRIVATE"

        reference.name = name
        reference.visibility = visibility
        reference.save(update_fields=["name", "visibility"])

    for inspection in Inspection.objects.select_related("master_version").all():
        if inspection.master_version_id:
            inspection.reference_name_snapshot = inspection.master_version.name
            inspection.save(update_fields=["reference_name_snapshot"])


def reverse_classification(apps, schema_editor):
    # The new fields are additive metadata. Reverse migration simply lets
    # Django remove them; legacy status/number fields remain untouched.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_proposal_withdrawn"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="masterversion",
            name="name",
            field=models.CharField(default="", max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="masterversion",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="inspection_references",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="masterversion",
            name="visibility",
            field=models.CharField(
                choices=[("SHARED", "مشترك"), ("PRIVATE", "خاص")],
                default="SHARED",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="inspection",
            name="reference_name_snapshot",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="inspection",
            name="master_version",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="inspections",
                to="core.masterversion",
            ),
        ),
        migrations.RunPython(classify_existing_references, reverse_classification),
        migrations.AlterModelOptions(
            name="masterversion",
            options={"ordering": ["name", "id"]},
        ),
    ]
