import uuid

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_snapshot_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="checklistitem",
            name="stable_id",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False),
        ),
        migrations.AddField(
            model_name="specificationdefinition",
            name="stable_id",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False),
        ),
        migrations.AddField(
            model_name="structurenode",
            name="stable_id",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False),
        ),
        migrations.AddField(
            model_name="proposal",
            name="source_local_id",
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="proposal",
            name="resolution_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name="institution",
            name="verification_status",
            field=models.CharField(
                choices=[
                    ("PENDING", "قيد المراجعة"),
                    ("VERIFIED", "معتمدة"),
                    ("REJECTED", "مرفوضة"),
                ],
                default="VERIFIED",
                max_length=16,
            ),
        ),
    ]
