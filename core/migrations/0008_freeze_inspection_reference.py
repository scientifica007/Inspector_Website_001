from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def freeze_existing_inspections(apps, schema_editor):
    MasterVersion = apps.get_model("core", "MasterVersion")
    StructureNode = apps.get_model("core", "StructureNode")
    SpecificationDefinition = apps.get_model("core", "SpecificationDefinition")
    ChecklistItem = apps.get_model("core", "ChecklistItem")
    Inspection = apps.get_model("core", "Inspection")
    InspectionNode = apps.get_model("core", "InspectionNode")
    SpecificationValue = apps.get_model("core", "SpecificationValue")
    InspectionItemResult = apps.get_model("core", "InspectionItemResult")

    next_number = (
        MasterVersion.objects.order_by("-number").values_list("number", flat=True).first()
        or 0
    )

    for inspection in Inspection.objects.select_related("master_version").order_by("id"):
        source = inspection.master_version
        if source is None or source.visibility == "SNAPSHOT":
            continue

        next_number += 1
        frozen = MasterVersion.objects.create(
            number=next_number,
            name=source.name,
            visibility="SNAPSHOT",
            owner_id=None,
            status="DRAFT",
        )

        source_nodes = {
            node.id: node
            for node in StructureNode.objects.filter(
                master_version_id=source.id
            ).order_by("id")
        }
        node_map = {}

        def clone_node(old_id):
            if old_id in node_map:
                return node_map[old_id]
            old = source_nodes[old_id]
            parent = clone_node(old.parent_id) if old.parent_id else None
            new = StructureNode.objects.create(
                stable_id=old.stable_id,
                master_version_id=frozen.id,
                parent_id=parent.id if parent else None,
                title=old.title,
                description=old.description,
                inspectable=old.inspectable,
                sort_order=old.sort_order,
                active=old.active,
            )
            node_map[old_id] = new
            return new

        for old_id in source_nodes:
            clone_node(old_id)

        spec_map = {}
        for old in SpecificationDefinition.objects.filter(
            node__master_version_id=source.id
        ).order_by("id"):
            new = SpecificationDefinition.objects.create(
                stable_id=old.stable_id,
                node_id=node_map[old.node_id].id,
                title=old.title,
                field_type=old.field_type,
                required=old.required,
                options=list(old.options or []),
                help_text=old.help_text,
                sort_order=old.sort_order,
                active=old.active,
            )
            spec_map[old.id] = new.id

        item_map = {}
        for old in ChecklistItem.objects.filter(
            node__master_version_id=source.id
        ).order_by("id"):
            new = ChecklistItem.objects.create(
                stable_id=old.stable_id,
                node_id=node_map[old.node_id].id,
                title=old.title,
                guidance=old.guidance,
                sort_order=old.sort_order,
                active=old.active,
            )
            item_map[old.id] = new.id

        for snapshot in InspectionNode.objects.filter(
            inspection_id=inspection.id,
            source_node_id__in=node_map.keys(),
        ):
            snapshot.source_node_id = node_map[snapshot.source_node_id].id
            snapshot.save(update_fields=["source_node"])

        for value in SpecificationValue.objects.filter(
            inspection_node__inspection_id=inspection.id,
            source_specification_id__in=spec_map.keys(),
        ):
            value.source_specification_id = spec_map[value.source_specification_id]
            value.save(update_fields=["source_specification"])

        for result in InspectionItemResult.objects.filter(
            inspection_node__inspection_id=inspection.id,
            source_item_id__in=item_map.keys(),
        ):
            result.source_item_id = item_map[result.source_item_id]
            result.save(update_fields=["source_item"])

        inspection.source_reference_id = source.id
        if not inspection.reference_name_snapshot:
            inspection.reference_name_snapshot = source.name
        inspection.master_version_id = frozen.id
        inspection.save(
            update_fields=[
                "source_reference",
                "reference_name_snapshot",
                "master_version",
            ]
        )


def unfreeze_existing_inspections(apps, schema_editor):
    MasterVersion = apps.get_model("core", "MasterVersion")
    StructureNode = apps.get_model("core", "StructureNode")
    SpecificationDefinition = apps.get_model("core", "SpecificationDefinition")
    ChecklistItem = apps.get_model("core", "ChecklistItem")
    Inspection = apps.get_model("core", "Inspection")
    InspectionNode = apps.get_model("core", "InspectionNode")
    SpecificationValue = apps.get_model("core", "SpecificationValue")
    InspectionItemResult = apps.get_model("core", "InspectionItemResult")

    frozen_ids = []

    for inspection in Inspection.objects.select_related(
        "master_version", "source_reference"
    ).order_by("id"):
        frozen = inspection.master_version
        if frozen is None or frozen.visibility != "SNAPSHOT":
            continue

        source = inspection.source_reference
        if source is not None:
            source_nodes = {
                str(node.stable_id): node.id
                for node in StructureNode.objects.filter(master_version_id=source.id)
            }
            source_specs = {
                str(spec.stable_id): spec.id
                for spec in SpecificationDefinition.objects.filter(
                    node__master_version_id=source.id
                )
            }
            source_items = {
                str(item.stable_id): item.id
                for item in ChecklistItem.objects.filter(
                    node__master_version_id=source.id
                )
            }

            for snapshot in InspectionNode.objects.filter(
                inspection_id=inspection.id,
                source_node__master_version_id=frozen.id,
            ).select_related("source_node"):
                snapshot.source_node_id = source_nodes.get(
                    str(snapshot.source_node.stable_id)
                )
                snapshot.save(update_fields=["source_node"])

            for value in SpecificationValue.objects.filter(
                inspection_node__inspection_id=inspection.id,
                source_specification__node__master_version_id=frozen.id,
            ).select_related("source_specification"):
                value.source_specification_id = source_specs.get(
                    str(value.source_specification.stable_id)
                )
                value.save(update_fields=["source_specification"])

            for result in InspectionItemResult.objects.filter(
                inspection_node__inspection_id=inspection.id,
                source_item__node__master_version_id=frozen.id,
            ).select_related("source_item"):
                result.source_item_id = source_items.get(
                    str(result.source_item.stable_id)
                )
                result.save(update_fields=["source_item"])
        else:
            InspectionNode.objects.filter(
                inspection_id=inspection.id,
                source_node__master_version_id=frozen.id,
            ).update(source_node=None)
            SpecificationValue.objects.filter(
                inspection_node__inspection_id=inspection.id,
                source_specification__node__master_version_id=frozen.id,
            ).update(source_specification=None)
            InspectionItemResult.objects.filter(
                inspection_node__inspection_id=inspection.id,
                source_item__node__master_version_id=frozen.id,
            ).update(source_item=None)

        frozen_ids.append(frozen.id)
        inspection.master_version_id = source.id if source else None
        inspection.source_reference_id = None
        inspection.save(update_fields=["master_version", "source_reference"])

    MasterVersion.objects.filter(id__in=frozen_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_private_reference_submission"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="masterversion",
            name="visibility",
            field=models.CharField(
                choices=[
                    ("SHARED", "مشترك"),
                    ("PRIVATE", "خاص"),
                    ("SNAPSHOT", "لقطة زيارة داخلية"),
                ],
                default="SHARED",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="inspection",
            name="source_reference",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="source_inspections",
                to="core.masterversion",
            ),
        ),
        migrations.RunPython(
            freeze_existing_inspections,
            unfreeze_existing_inspections,
        ),
    ]
