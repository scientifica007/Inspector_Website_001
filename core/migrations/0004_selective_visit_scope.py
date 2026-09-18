from django.db import migrations, models


def migrate_existing_scope(apps, schema_editor):
    InspectionNode = apps.get_model("core", "InspectionNode")
    SpecificationValue = apps.get_model("core", "SpecificationValue")
    InspectionItemResult = apps.get_model("core", "InspectionItemResult")

    InspectionNode.objects.filter(local_addition=True).update(scope_origin="LOCAL")
    InspectionNode.objects.filter(local_addition=False).update(scope_origin="LEGACY")

    SpecificationValue.objects.filter(local_addition=True).update(scope_origin="LOCAL")
    SpecificationValue.objects.filter(local_addition=False).update(scope_origin="LEGACY")

    InspectionItemResult.objects.filter(local_addition=True).update(scope_origin="LOCAL")
    InspectionItemResult.objects.filter(local_addition=False).update(scope_origin="LEGACY")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_governance_stable_ids"),
    ]

    operations = [
        migrations.AddField(
            model_name="inspection",
            name="scope_mode",
            field=models.CharField(
                choices=[
                    ("LEGACY_FULL", "نطاق تاريخي كامل"),
                    ("SELECTIVE", "نطاق انتقائي"),
                ],
                default="LEGACY_FULL",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="inspectionnode",
            name="scope_origin",
            field=models.CharField(
                choices=[
                    ("LEGACY", "تاريخي"),
                    ("MANUAL", "اختيار المفتش"),
                    ("GUIDE", "دليل مقترح"),
                    ("ASSIGNMENT", "تكليف"),
                    ("LOCAL", "إضافة محلية"),
                ],
                default="LEGACY",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="inspectionnode",
            name="scope_state",
            field=models.CharField(
                choices=[("ACTIVE", "ضمن النطاق"), ("EXCLUDED", "مستبعد")],
                default="ACTIVE",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="inspectionnode",
            name="scope_role",
            field=models.CharField(
                choices=[("SELECTED", "مختار"), ("CONTEXT", "سياق بنيوي")],
                default="SELECTED",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="inspectionnode",
            name="scope_locked",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="specificationvalue",
            name="scope_origin",
            field=models.CharField(
                choices=[
                    ("LEGACY", "تاريخي"),
                    ("MANUAL", "اختيار المفتش"),
                    ("GUIDE", "دليل مقترح"),
                    ("ASSIGNMENT", "تكليف"),
                    ("LOCAL", "إضافة محلية"),
                ],
                default="LEGACY",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="specificationvalue",
            name="scope_state",
            field=models.CharField(
                choices=[("ACTIVE", "ضمن النطاق"), ("EXCLUDED", "مستبعد")],
                default="ACTIVE",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="specificationvalue",
            name="scope_locked",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="specificationvalue",
            name="completion_required",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="inspectionitemresult",
            name="scope_origin",
            field=models.CharField(
                choices=[
                    ("LEGACY", "تاريخي"),
                    ("MANUAL", "اختيار المفتش"),
                    ("GUIDE", "دليل مقترح"),
                    ("ASSIGNMENT", "تكليف"),
                    ("LOCAL", "إضافة محلية"),
                ],
                default="LEGACY",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="inspectionitemresult",
            name="scope_state",
            field=models.CharField(
                choices=[("ACTIVE", "ضمن النطاق"), ("EXCLUDED", "مستبعد")],
                default="ACTIVE",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="inspectionitemresult",
            name="scope_locked",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="inspectionitemresult",
            name="completion_required",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(migrate_existing_scope, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="inspectionnode",
            name="local_addition",
        ),
        migrations.RemoveField(
            model_name="specificationvalue",
            name="local_addition",
        ),
        migrations.RemoveField(
            model_name="inspectionitemresult",
            name="local_addition",
        ),
        migrations.AlterField(
            model_name="inspection",
            name="scope_mode",
            field=models.CharField(
                choices=[
                    ("LEGACY_FULL", "نطاق تاريخي كامل"),
                    ("SELECTIVE", "نطاق انتقائي"),
                ],
                default="SELECTIVE",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="inspectionnode",
            name="scope_origin",
            field=models.CharField(
                choices=[
                    ("LEGACY", "تاريخي"),
                    ("MANUAL", "اختيار المفتش"),
                    ("GUIDE", "دليل مقترح"),
                    ("ASSIGNMENT", "تكليف"),
                    ("LOCAL", "إضافة محلية"),
                ],
                default="MANUAL",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="specificationvalue",
            name="scope_origin",
            field=models.CharField(
                choices=[
                    ("LEGACY", "تاريخي"),
                    ("MANUAL", "اختيار المفتش"),
                    ("GUIDE", "دليل مقترح"),
                    ("ASSIGNMENT", "تكليف"),
                    ("LOCAL", "إضافة محلية"),
                ],
                default="MANUAL",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="inspectionitemresult",
            name="scope_origin",
            field=models.CharField(
                choices=[
                    ("LEGACY", "تاريخي"),
                    ("MANUAL", "اختيار المفتش"),
                    ("GUIDE", "دليل مقترح"),
                    ("ASSIGNMENT", "تكليف"),
                    ("LOCAL", "إضافة محلية"),
                ],
                default="MANUAL",
                max_length=16,
            ),
        ),
        migrations.AddConstraint(
            model_name="inspectionnode",
            constraint=models.UniqueConstraint(
                condition=models.Q(("source_node__isnull", False)),
                fields=("inspection", "source_node"),
                name="uq_inspection_source_node",
            ),
        ),
        migrations.AddConstraint(
            model_name="specificationvalue",
            constraint=models.UniqueConstraint(
                condition=models.Q(("source_specification__isnull", False)),
                fields=("inspection_node", "source_specification"),
                name="uq_inspection_node_source_spec",
            ),
        ),
        migrations.AddConstraint(
            model_name="inspectionitemresult",
            constraint=models.UniqueConstraint(
                condition=models.Q(("source_item__isnull", False)),
                fields=("inspection_node", "source_item"),
                name="uq_inspection_node_source_item",
            ),
        ),
    ]
