# Generated manually for Gate 4; verified by Django migration drift check.
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="inspectionitemresult",
            name="guidance_snapshot",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="specificationvalue",
            name="help_text_snapshot",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="specificationvalue",
            name="options_snapshot",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="specificationvalue",
            name="required_snapshot",
            field=models.BooleanField(default=False),
        ),
    ]
