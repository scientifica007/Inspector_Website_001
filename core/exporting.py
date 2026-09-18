EXPORT_SCHEMA = "inspection-export-v1"

from .models import ProposalType

def _proposal_index(inspection):
    index = {}
    for proposal in inspection.proposals.all().order_by("id"):
        if proposal.source_local_id is None:
            continue
        index[(proposal.proposal_type, proposal.source_local_id)] = proposal
    return index

def _proposal_trace(index, proposal_type, local_id):
    proposal = index.get((proposal_type, local_id))
    if proposal is None:
        return None
    return {
        "proposal_id": proposal.id,
        "status": proposal.status,
        "resolution_data": proposal.resolution_data or {},
    }

def build_inspection_export(inspection):
    proposal_index = _proposal_index(inspection)
    nodes = list(
        inspection.inspection_nodes.select_related("source_node").order_by(
            "sort_order_snapshot", "id"
        )
    )
    children = {}
    for node in nodes:
        children.setdefault(node.parent_id, []).append(node)

    def node_payload(node):
        specifications = []
        for spec in node.specification_values.select_related(
            "source_specification"
        ).order_by("sort_order_snapshot", "id"):
            payload = {
                "snapshot_id": spec.id,
                "source_stable_id": (
                    str(spec.source_specification.stable_id)
                    if spec.source_specification_id
                    else None
                ),
                "title": spec.title_snapshot,
                "field_type": spec.field_type_snapshot,
                "required": spec.required_snapshot,
                "options": list(spec.options_snapshot or []),
                "help_text": spec.help_text_snapshot,
                "value": spec.value,
                "local_addition": spec.local_addition,
            }
            if spec.local_addition:
                payload["proposal"] = _proposal_trace(
                    proposal_index, ProposalType.SPECIFICATION, spec.id
                )
            specifications.append(payload)

        items = []
        for item in node.item_results.select_related("source_item").order_by(
            "sort_order_snapshot", "id"
        ):
            payload = {
                "snapshot_id": item.id,
                "source_stable_id": (
                    str(item.source_item.stable_id) if item.source_item_id else None
                ),
                "title": item.title_snapshot,
                "guidance": item.guidance_snapshot,
                "status": item.status,
                "observation": item.observation,
                "local_addition": item.local_addition,
            }
            if item.local_addition:
                payload["proposal"] = _proposal_trace(
                    proposal_index, ProposalType.ITEM, item.id
                )
            items.append(payload)

        payload = {
            "snapshot_id": node.id,
            "source_stable_id": (
                str(node.source_node.stable_id) if node.source_node_id else None
            ),
            "title": node.title_snapshot,
            "description": node.description_snapshot,
            "local_addition": node.local_addition,
            "specifications": specifications,
            "checklist_items": items,
            "additional_observations": node.additional_observations,
            "recommendations": node.recommendations,
            "children": [node_payload(child) for child in children.get(node.id, [])],
        }
        if node.local_addition:
            payload["proposal"] = _proposal_trace(
                proposal_index, ProposalType.NODE, node.id
            )
        return payload

    return {
        "schema": EXPORT_SCHEMA,
        "inspection": {
            "id": inspection.id,
            "visit_date": inspection.visit_date.isoformat(),
            "status": inspection.status,
            "institution": {
                "id": inspection.institution_id,
                "name": inspection.institution.name,
                "type": inspection.institution.institution_type,
                "commune": inspection.institution.commune,
            },
            "inspector": {
                "id": inspection.inspector_id,
                "username": inspection.inspector.username,
            },
            "master_version": {
                "id": inspection.master_version_id,
                "number": inspection.master_version.number,
            },
            "general_observations": inspection.general_observations,
            "general_recommendations": inspection.general_recommendations,
            "nodes": [node_payload(node) for node in children.get(None, [])],
        },
    }
