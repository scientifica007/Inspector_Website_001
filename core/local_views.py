from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render

from .governance_forms import LocalItemForm, LocalNodeForm, LocalSpecificationForm
from .models import (
    InspectionItemResult,
    InspectionNode,
    InspectionScopeMode,
    InspectionStatus,
    Proposal,
    ProposalType,
    ScopeOrigin,
    ScopeRole,
    ScopeState,
    SpecificationValue,
)
from .views import inspection_for_user

def _owned_editable_inspection(request, pk):
    inspection = inspection_for_user(request.user, pk)
    if inspection.inspector_id != request.user.id:
        raise PermissionDenied("الإضافة المحلية متاحة للمفتش صاحب الزيارة فقط.")
    if inspection.status != InspectionStatus.DRAFT:
        raise PermissionDenied("لا يمكن الإضافة إلى زيارة مكتملة.")
    return inspection

def _target_payload(node):
    if node.source_node_id:
        return {"target_node_stable_id": str(node.source_node.stable_id)}
    return {"target_local_node_id": node.id}

def _next_order(queryset, field_name):
    current = queryset.aggregate(value=Max(field_name))["value"]
    return (current or 0) + 10

def _mark_selective(inspection):
    if inspection.scope_mode != InspectionScopeMode.SELECTIVE:
        inspection.scope_mode = InspectionScopeMode.SELECTIVE
        inspection.save(update_fields=["scope_mode", "updated_at"])

def _active_node(inspection, node_pk):
    return get_object_or_404(
        InspectionNode.objects.select_related("source_node"),
        pk=node_pk,
        inspection=inspection,
        scope_state=ScopeState.ACTIVE,
    )

@login_required
def local_root_node_add(request, inspection_pk):
    inspection = _owned_editable_inspection(request, inspection_pk)
    form = LocalNodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            order = _next_order(
                inspection.inspection_nodes.filter(parent__isnull=True),
                "sort_order_snapshot",
            )
            local = InspectionNode.objects.create(
                inspection=inspection,
                parent=None,
                title_snapshot=form.cleaned_data["title"].strip(),
                description_snapshot=form.cleaned_data["description"].strip(),
                sort_order_snapshot=order,
                scope_origin=ScopeOrigin.LOCAL,
                scope_state=ScopeState.ACTIVE,
                scope_role=ScopeRole.SELECTED,
            )
            Proposal.objects.create(
                proposal_type=ProposalType.NODE,
                source_inspection=inspection,
                source_local_id=local.id,
                proposed_by=request.user,
                payload={
                    "target_root": True,
                    "title": local.title_snapshot,
                    "description": local.description_snapshot,
                    "inspectable": form.cleaned_data["inspectable"],
                    "sort_order": order,
                },
            )
            _mark_selective(inspection)
        messages.success(
            request,
            "أضيف العنصر المحلي الرئيسي إلى الزيارة وأرسل كاقتراح للإدارة.",
        )
        return redirect("inspection_node_prepare", inspection_pk=inspection.pk, node_pk=local.pk)

    return render(
        request,
        "core/local_addition_form.html",
        {
            "inspection": inspection,
            "node": None,
            "form": form,
            "title": "إضافة عنصر محلي رئيسي",
        },
    )

@login_required
def local_node_add(request, inspection_pk, node_pk):
    inspection = _owned_editable_inspection(request, inspection_pk)
    parent = _active_node(inspection, node_pk)
    form = LocalNodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            order = _next_order(parent.children.all(), "sort_order_snapshot")
            local = InspectionNode.objects.create(
                inspection=inspection,
                parent=parent,
                title_snapshot=form.cleaned_data["title"].strip(),
                description_snapshot=form.cleaned_data["description"].strip(),
                sort_order_snapshot=order,
                scope_origin=ScopeOrigin.LOCAL,
                scope_state=ScopeState.ACTIVE,
                scope_role=ScopeRole.SELECTED,
            )
            payload = {
                **_target_payload(parent),
                "title": local.title_snapshot,
                "description": local.description_snapshot,
                "inspectable": form.cleaned_data["inspectable"],
                "sort_order": order,
            }
            Proposal.objects.create(
                proposal_type=ProposalType.NODE,
                source_inspection=inspection,
                source_local_id=local.id,
                proposed_by=request.user,
                payload=payload,
            )
            _mark_selective(inspection)
        messages.success(request, "أضيف الفرع إلى هذه الزيارة وأرسل كاقتراح للإدارة.")
        return redirect("inspection_node_prepare", inspection_pk=inspection.pk, node_pk=local.pk)

    return render(
        request,
        "core/local_addition_form.html",
        {"inspection": inspection, "node": parent, "form": form, "title": "إضافة فرع محلي"},
    )

@login_required
def local_specification_add(request, inspection_pk, node_pk):
    inspection = _owned_editable_inspection(request, inspection_pk)
    node = _active_node(inspection, node_pk)
    form = LocalSpecificationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            order = _next_order(node.specification_values.all(), "sort_order_snapshot")
            spec = SpecificationValue.objects.create(
                inspection_node=node,
                title_snapshot=form.cleaned_data["title"].strip(),
                field_type_snapshot=form.cleaned_data["field_type"],
                required_snapshot=form.cleaned_data["required"],
                options_snapshot=form.cleaned_data["options"],
                help_text_snapshot=form.cleaned_data["help_text"].strip(),
                sort_order_snapshot=order,
                scope_origin=ScopeOrigin.LOCAL,
                scope_state=ScopeState.ACTIVE,
            )
            payload = {
                **_target_payload(node),
                "title": spec.title_snapshot,
                "field_type": spec.field_type_snapshot,
                "required": spec.required_snapshot,
                "options": list(spec.options_snapshot or []),
                "help_text": spec.help_text_snapshot,
                "sort_order": order,
            }
            Proposal.objects.create(
                proposal_type=ProposalType.SPECIFICATION,
                source_inspection=inspection,
                source_local_id=spec.id,
                proposed_by=request.user,
                payload=payload,
            )
            _mark_selective(inspection)
        messages.success(request, "أضيف الوصف إلى الزيارة وأرسل كاقتراح للإدارة.")
        return redirect("inspection_node_prepare", inspection_pk=inspection.pk, node_pk=node.pk)

    return render(
        request,
        "core/local_addition_form.html",
        {"inspection": inspection, "node": node, "form": form, "title": "إضافة وصف محلي"},
    )

@login_required
def local_item_add(request, inspection_pk, node_pk):
    inspection = _owned_editable_inspection(request, inspection_pk)
    node = _active_node(inspection, node_pk)
    form = LocalItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            order = _next_order(node.item_results.all(), "sort_order_snapshot")
            item = InspectionItemResult.objects.create(
                inspection_node=node,
                title_snapshot=form.cleaned_data["title"].strip(),
                guidance_snapshot=form.cleaned_data["guidance"].strip(),
                sort_order_snapshot=order,
                scope_origin=ScopeOrigin.LOCAL,
                scope_state=ScopeState.ACTIVE,
            )
            payload = {
                **_target_payload(node),
                "title": item.title_snapshot,
                "guidance": item.guidance_snapshot,
                "sort_order": order,
            }
            Proposal.objects.create(
                proposal_type=ProposalType.ITEM,
                source_inspection=inspection,
                source_local_id=item.id,
                proposed_by=request.user,
                payload=payload,
            )
            _mark_selective(inspection)
        messages.success(request, "أضيف بند التفتيش إلى الزيارة وأرسل كاقتراح للإدارة.")
        return redirect("inspection_node_prepare", inspection_pk=inspection.pk, node_pk=node.pk)

    return render(
        request,
        "core/local_addition_form.html",
        {"inspection": inspection, "node": node, "form": form, "title": "إضافة بند محلي"},
    )
