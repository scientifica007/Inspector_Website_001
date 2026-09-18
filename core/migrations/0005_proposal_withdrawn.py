from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_selective_visit_scope"),
    ]

    operations = [
        migrations.AlterField(
            model_name="proposal",
            name="proposal_type",
            field=models.CharField(
                choices=[
                    ("INSTITUTION", "مؤسسة"),
                    ("NODE", "عنصر هيكلي"),
                    ("SPECIFICATION", "وصف"),
                    ("ITEM", "بند"),
                ],
                max_length=24,
            ),
        ),
        migrations.AlterField(
            model_name="proposal",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "قيد المراجعة"),
                    ("APPROVED", "معتمد"),
                    ("REJECTED", "مرفوض"),
                    ("MERGED", "مدمج"),
                    ("WITHDRAWN", "مسحوب"),
                ],
                default="PENDING",
                max_length=16,
            ),
        ),
    ]
