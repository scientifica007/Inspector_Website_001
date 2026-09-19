from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max, Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from .governance_forms import (
    LocalItemForm,
    LocalNodeForm,
    LocalSpecificationForm,
    LocalTargetForm,
)
from .local_authoring import (
    copy_item_as_local,
    copy_node_as_local,
    copy_specification_as_local,
    move_local_item,
    move_local_node,
    move_local_specification,
    node_inspectable,
    node_subtree_ids,
    remove_local_item,
    remove_local_node,
    remove_local_specification,
    restore_local_item,
    restore_local_node,
    restore_local_specification,
    update_local_item,
    update_local_node,
    update_local_specification,
)
from .models import (
    InspectionItemResult,
    InspectionNode,
    InspectionScopeMode,
    InspectionStatus,
    ScopeOrigin,
    ScopeRole,
    ScopeState,
    SpecificationValue,
)
from .views import inspection_for_user


def _owned_editable_inspection(request, pk):
    inspection = inspection_for_user(request.user, pk)
    if inspection.inspector_id != request.user.id:
        raise PermissionDenied("تحرير الزيارة متاح للمفتش صاحبها فقط.")
    if inspection.status != InspectionStatus.DRAFT:
        raise PermissionDenied("لا يمكن تعديل زيارة مكتملة.")
    return inspection


def _next_order(queryset, field_name):
    current = queryset.aggregate(value=Max(field_name))["value"]
    return (current or 0) + 10


def _mark_selective(inspection):
    if inspection.scope_mode != InspectionScopeMode.SELECTIVE:
        inspection.scope_mode = InspectionScopeMode.SELECTIVE
        inspection.save(update_fields=["scope_mode", "updated_at"])


def _active_node(inspection, node_pk):
    return get_object_or_404(
        InspectionNode.objects.select_related("source_node", "parent"),
        pk=node_pk,
        inspection=inspection,
        scope_state=ScopeState.ACTIVE,
    )


def _local_node(inspection, node_pk, *, state=ScopeState.ACTIVE):
    return get_object_or_404(
        InspectionNode.objects.select_related("source_node", "parent"),
        pk=node_pk,
        inspection=inspection,
        scope_origin=ScopeOrigin.LOCAL,
        scope_state=state,
    )


def _local_specification(inspection, spec_pk, *, state=ScopeState.ACTIVE):
    return get_object_or_404(
        SpecificationValue.objects.select_related(
            "inspection_node",
            "inspection_node__inspection",
        ),
        pk=spec_pk,
        inspection_node__inspection=inspection,
        scope_origin=ScopeOrigin.LOCAL,
        scope_state=state,
    )


def _local_item(inspection, item_pk, *, state=ScopeState.ACTIVE):
    return get_object_or_404(
        InspectionItemResult.objects.select_related(
            "inspection_node",
            "inspection_node__inspection",
        ),
        pk=item_pk,
        inspection_node__inspection=inspection,
        scope_origin=ScopeOrigin.LOCAL,
        scope_state=state,
    )


def _active_specification(inspection, spec_pk):
    return get_object_or_404(
        SpecificationValue.objects.select_related("inspection_node"),
        pk=spec_pk,
        inspection_node__inspection=inspection,
        inspection_node__scope_state=ScopeState.ACTIVE,
        scope_state=ScopeState.ACTIVE,
    )


def _active_item(inspection, item_pk):
    return get_object_or_404(
        InspectionItemResult.objects.select_related("inspection_node"),
        pk=item_pk,
        inspection_node__inspection=inspection,
        inspection_node__scope_state=ScopeState.ACTIVE,
        scope_state=ScopeState.ACTIVE,
    )


def _render_author_form(
    request,
    *,
    inspection,
    node,
    form,
    title,
    button_label,
    hint,
):
    return render(
        request,
        "core/local_addition_form.html",
        {
            "inspection": inspection,
            "node": node,
            "form": form,
            "title": title,
            "button_label": button_label,
            "hint": hint,
        },
    )


def _render_transfer_form(
    request,
    *,
    inspection,
    form,
    title,
    source_label,
    button_label,
    cancel_node=None,
):
    return render(
        request,
        "core/local_transfer_form.html",
        {
            "inspection": inspection,
            "form": form,
            "title": title,
            "source_label": source_label,
            "button_label": button_label,
            "cancel_node": cancel_node,
        },
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
                inspectable_snapshot=form.cleaned_data["inspectable"],
                sort_order_snapshot=order,
                scope_origin=ScopeOrigin.LOCAL,
                scope_state=ScopeState.ACTIVE,
                scope_role=ScopeRole.SELECTED,
            )
            _mark_selective(inspection)
        messages.success(
            request,
            "أضيف العنصر المحلي الرئيسي إلى الزيارة وحُفظ داخل الزيارة فقط.",
        )
        return redirect(
            "inspection_node_prepare",
            inspection_pk=inspection.pk,
            node_pk=local.pk,
        )

    return _render_author_form(
        request,
        inspection=inspection,
        node=None,
        form=form,
        title="إضافة عنصر محلي رئيسي",
        button_label="إضافة إلى الزيارة",
        hint="يظهر العنصر فورًا في التحضير ويبقى خاصًا بهذه الزيارة.",
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
                inspectable_snapshot=form.cleaned_data["inspectable"],
                sort_order_snapshot=order,
                scope_origin=ScopeOrigin.LOCAL,
                scope_state=ScopeState.ACTIVE,
                scope_role=ScopeRole.SELECTED,
            )
            _mark_selective(inspection)
        messages.success(request, "أضيف الفرع إلى هذه الزيارة وحُفظ داخل الزيارة فقط.")
        return redirect(
            "inspection_node_prepare",
            inspection_pk=inspection.pk,
            node_pk=local.pk,
        )

    return _render_author_form(
        request,
        inspection=inspection,
        node=parent,
        form=form,
        title="إضافة فرع محلي",
        button_label="إضافة إلى الزيارة",
        hint="يظهر الفرع فورًا في التحضير ويبقى خاصًا بهذه الزيارة.",
    )


@login_required
def local_specification_add(request, inspection_pk, node_pk):
    inspection = _owned_editable_inspection(request, inspection_pk)
    node = _active_node(inspection, node_pk)
    form = LocalSpecificationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            order = _next_order(
                node.specification_values.all(),
                "sort_order_snapshot",
            )
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
            _mark_selective(inspection)
        messages.success(request, "أضيف الوصف إلى الزيارة وحُفظ داخل الزيارة فقط.")
        return redirect(
            "inspection_node_prepare",
            inspection_pk=inspection.pk,
            node_pk=node.pk,
        )

    return _render_author_form(
        request,
        inspection=inspection,
        node=node,
        form=form,
        title="إضافة وصف محلي",
        button_label="إضافة إلى الزيارة",
        hint="عرّف الوصف هنا؛ قيمته الميدانية تُدخل لاحقًا في مساحة التنفيذ.",
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
            _mark_selective(inspection)
        messages.success(request, "أضيف بند التفتيش إلى الزيارة وحُفظ داخل الزيارة فقط.")
        return redirect(
            "inspection_node_prepare",
            inspection_pk=inspection.pk,
            node_pk=node.pk,
        )

    return _render_author_form(
        request,
        inspection=inspection,
        node=node,
        form=form,
        title="إضافة بند محلي",
        button_label="إضافة إلى الزيارة",
        hint="أضف صياغة البند وتوجيهه؛ الحالة والمعاينة تُدخلان أثناء التنفيذ.",
    )


@login_required
def local_node_edit(request, inspection_pk, node_pk):
    inspection = _owned_editable_inspection(request, inspection_pk)
    node = _local_node(inspection, node_pk)
    form = LocalNodeForm(
        request.POST or None,
        initial={
            "title": node.title_snapshot,
            "description": node.description_snapshot,
            "inspectable": node_inspectable(node),
        },
    )
    if request.method == "POST" and form.is_valid():
        update_local_node(node, request.user, form.cleaned_data)
        messages.success(request, "تم تعديل الفرع المحلي وحُفظ التعديل داخل الزيارة.")
        return redirect(
            "inspection_node_prepare",
            inspection_pk=inspection.pk,
            node_pk=node.pk,
        )
    return _render_author_form(
        request,
        inspection=inspection,
        node=node,
        form=form,
        title="تعديل الفرع المحلي",
        button_label="حفظ التعديل",
        hint="هذا تعديل محلي داخل الزيارة ولا يُرسل تلقائيًا إلى الإدارة.",
    )


@login_required
def local_specification_edit(request, inspection_pk, spec_pk):
    inspection = _owned_editable_inspection(request, inspection_pk)
    spec = _local_specification(inspection, spec_pk)
    form = LocalSpecificationForm(
        request.POST or None,
        initial={
            "title": spec.title_snapshot,
            "field_type": spec.field_type_snapshot,
            "required": spec.required_snapshot,
            "options_text": "\n".join(spec.options_snapshot or []),
            "help_text": spec.help_text_snapshot,
        },
    )
    if request.method == "POST" and form.is_valid():
        update_local_specification(spec, request.user, form.cleaned_data)
        messages.success(request, "تم تعديل الوصف المحلي وحُفظ التعديل داخل الزيارة.")
        return redirect(
            "inspection_node_prepare",
            inspection_pk=inspection.pk,
            node_pk=spec.inspection_node_id,
        )
    return _render_author_form(
        request,
        inspection=inspection,
        node=spec.inspection_node,
        form=form,
        title="تعديل الوصف المحلي",
        button_label="حفظ التعديل",
        hint="تغيير نوع القيمة أو خياراتها يمسح القيمة الميدانية القديمة لتجنب بيانات غير صالحة.",
    )


@login_required
def local_item_edit(request, inspection_pk, item_pk):
    inspection = _owned_editable_inspection(request, inspection_pk)
    item = _local_item(inspection, item_pk)
    form = LocalItemForm(
        request.POST or None,
        initial={
            "title": item.title_snapshot,
            "guidance": item.guidance_snapshot,
        },
    )
    if request.method == "POST" and form.is_valid():
        update_local_item(item, request.user, form.cleaned_data)
        messages.success(request, "تم تعديل البند المحلي وحُفظ التعديل داخل الزيارة.")
        return redirect(
            "inspection_node_prepare",
            inspection_pk=inspection.pk,
            node_pk=item.inspection_node_id,
        )
    return _render_author_form(
        request,
        inspection=inspection,
        node=item.inspection_node,
        form=form,
        title="تعديل البند المحلي",
        button_label="حفظ التعديل",
        hint="تعديل صياغة البند لا يمحو نتيجة ميدانية موجودة.",
    )


@login_required
def local_node_duplicate(request, inspection_pk, node_pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    inspection = _owned_editable_inspection(request, inspection_pk)
    node = _active_node(inspection, node_pk)
    clone = copy_node_as_local(node, node.parent, request.user)
    messages.success(request, "تم إنشاء نسخة محلية مستقلة من الفرع ومحتواه.")
    return redirect(
        "inspection_node_prepare",
        inspection_pk=inspection.pk,
        node_pk=clone.pk,
    )


@login_required
def local_specification_duplicate(request, inspection_pk, spec_pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    inspection = _owned_editable_inspection(request, inspection_pk)
    spec = _active_specification(inspection, spec_pk)
    copy_specification_as_local(spec, spec.inspection_node, request.user)
    messages.success(request, "تم إنشاء نسخة محلية مستقلة من الوصف.")
    return redirect(
        "inspection_node_prepare",
        inspection_pk=inspection.pk,
        node_pk=spec.inspection_node_id,
    )


@login_required
def local_item_duplicate(request, inspection_pk, item_pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    inspection = _owned_editable_inspection(request, inspection_pk)
    item = _active_item(inspection, item_pk)
    copy_item_as_local(item, item.inspection_node, request.user)
    messages.success(request, "تم إنشاء نسخة محلية مستقلة من البند.")
    return redirect(
        "inspection_node_prepare",
        inspection_pk=inspection.pk,
        node_pk=item.inspection_node_id,
    )


@login_required
def local_node_copy(request, inspection_pk, node_pk):
    inspection = _owned_editable_inspection(request, inspection_pk)
    node = _active_node(inspection, node_pk)
    form = LocalTargetForm(
        request.POST or None,
        inspection=inspection,
        allow_root=True,
        exclude_node_ids=node_subtree_ids(node),
    )
    if request.method == "POST" and form.is_valid():
        clone = copy_node_as_local(
            node,
            form.cleaned_data["target_node"],
            request.user,
        )
        messages.success(request, "تم نسخ الفرع كمحتوى محلي مستقل في الوجهة المختارة.")
        return redirect(
            "inspection_node_prepare",
            inspection_pk=inspection.pk,
            node_pk=clone.pk,
        )
    return _render_transfer_form(
        request,
        inspection=inspection,
        form=form,
        title="نسخ الفرع",
        source_label=node.title_snapshot,
        button_label="نسخ إلى الوجهة",
        cancel_node=node,
    )


@login_required
def local_specification_copy(request, inspection_pk, spec_pk):
    inspection = _owned_editable_inspection(request, inspection_pk)
    spec = _active_specification(inspection, spec_pk)
    form = LocalTargetForm(request.POST or None, inspection=inspection)
    if request.method == "POST" and form.is_valid():
        target = form.cleaned_data["target_node"]
        copy_specification_as_local(spec, target, request.user)
        messages.success(request, "تم نسخ الوصف كمحتوى محلي مستقل.")
        return redirect(
            "inspection_node_prepare",
            inspection_pk=inspection.pk,
            node_pk=target.pk,
        )
    return _render_transfer_form(
        request,
        inspection=inspection,
        form=form,
        title="نسخ الوصف",
        source_label=spec.title_snapshot,
        button_label="نسخ إلى الوجهة",
        cancel_node=spec.inspection_node,
    )


@login_required
def local_item_copy(request, inspection_pk, item_pk):
    inspection = _owned_editable_inspection(request, inspection_pk)
    item = _active_item(inspection, item_pk)
    form = LocalTargetForm(request.POST or None, inspection=inspection)
    if request.method == "POST" and form.is_valid():
        target = form.cleaned_data["target_node"]
        copy_item_as_local(item, target, request.user)
        messages.success(request, "تم نسخ البند كمحتوى محلي مستقل.")
        return redirect(
            "inspection_node_prepare",
            inspection_pk=inspection.pk,
            node_pk=target.pk,
        )
    return _render_transfer_form(
        request,
        inspection=inspection,
        form=form,
        title="نسخ البند",
        source_label=item.title_snapshot,
        button_label="نسخ إلى الوجهة",
        cancel_node=item.inspection_node,
    )


@login_required
def local_node_move(request, inspection_pk, node_pk):
    inspection = _owned_editable_inspection(request, inspection_pk)
    node = _local_node(inspection, node_pk)
    form = LocalTargetForm(
        request.POST or None,
        inspection=inspection,
        allow_root=True,
        exclude_node_ids=node_subtree_ids(node),
    )
    if request.method == "POST" and form.is_valid():
        try:
            _, changed = move_local_node(
                node,
                form.cleaned_data["target_node"],
                request.user,
            )
        except ValidationError as exc:
            form.add_error(None, " ".join(exc.messages))
        else:
            messages.success(
                request,
                "تم نقل الفرع المحلي." if changed else "الفرع موجود أصلًا في هذه الوجهة.",
            )
            return redirect(
                "inspection_node_prepare",
                inspection_pk=inspection.pk,
                node_pk=node.pk,
            )
    return _render_transfer_form(
        request,
        inspection=inspection,
        form=form,
        title="نقل الفرع المحلي",
        source_label=node.title_snapshot,
        button_label="نقل إلى الوجهة",
        cancel_node=node,
    )


@login_required
def local_specification_move(request, inspection_pk, spec_pk):
    inspection = _owned_editable_inspection(request, inspection_pk)
    spec = _local_specification(inspection, spec_pk)
    form = LocalTargetForm(request.POST or None, inspection=inspection)
    if request.method == "POST" and form.is_valid():
        target = form.cleaned_data["target_node"]
        _, changed = move_local_specification(spec, target, request.user)
        messages.success(
            request,
            "تم نقل الوصف المحلي." if changed else "الوصف موجود أصلًا في هذه الوجهة.",
        )
        return redirect(
            "inspection_node_prepare",
            inspection_pk=inspection.pk,
            node_pk=target.pk,
        )
    return _render_transfer_form(
        request,
        inspection=inspection,
        form=form,
        title="نقل الوصف المحلي",
        source_label=spec.title_snapshot,
        button_label="نقل إلى الوجهة",
        cancel_node=spec.inspection_node,
    )


@login_required
def local_item_move(request, inspection_pk, item_pk):
    inspection = _owned_editable_inspection(request, inspection_pk)
    item = _local_item(inspection, item_pk)
    form = LocalTargetForm(request.POST or None, inspection=inspection)
    if request.method == "POST" and form.is_valid():
        target = form.cleaned_data["target_node"]
        _, changed = move_local_item(item, target, request.user)
        messages.success(
            request,
            "تم نقل البند المحلي." if changed else "البند موجود أصلًا في هذه الوجهة.",
        )
        return redirect(
            "inspection_node_prepare",
            inspection_pk=inspection.pk,
            node_pk=target.pk,
        )
    return _render_transfer_form(
        request,
        inspection=inspection,
        form=form,
        title="نقل البند المحلي",
        source_label=item.title_snapshot,
        button_label="نقل إلى الوجهة",
        cancel_node=item.inspection_node,
    )


@login_required
def local_node_remove(request, inspection_pk, node_pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    inspection = _owned_editable_inspection(request, inspection_pk)
    node = _local_node(inspection, node_pk)
    parent = node.parent
    remove_local_node(node, request.user)
    messages.success(request, "أُخرج الفرع المحلي مع حفظه وإمكانية استعادته.")
    if parent and parent.scope_state == ScopeState.ACTIVE:
        return redirect(
            "inspection_node_prepare",
            inspection_pk=inspection.pk,
            node_pk=parent.pk,
        )
    return redirect("inspection_prepare", pk=inspection.pk)


@login_required
def local_specification_remove(request, inspection_pk, spec_pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    inspection = _owned_editable_inspection(request, inspection_pk)
    spec = _local_specification(inspection, spec_pk)
    node_pk = spec.inspection_node_id
    remove_local_specification(spec, request.user)
    messages.success(request, "أُخرج الوصف المحلي مع حفظه وإمكانية استعادته.")
    return redirect(
        "inspection_node_prepare",
        inspection_pk=inspection.pk,
        node_pk=node_pk,
    )


@login_required
def local_item_remove(request, inspection_pk, item_pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    inspection = _owned_editable_inspection(request, inspection_pk)
    item = _local_item(inspection, item_pk)
    node_pk = item.inspection_node_id
    remove_local_item(item, request.user)
    messages.success(request, "أُخرج البند المحلي مع حفظه وإمكانية استعادته.")
    return redirect(
        "inspection_node_prepare",
        inspection_pk=inspection.pk,
        node_pk=node_pk,
    )


@login_required
def local_removed_content(request, inspection_pk):
    inspection = _owned_editable_inspection(request, inspection_pk)
    nodes = (
        InspectionNode.objects.filter(
            inspection=inspection,
            scope_origin=ScopeOrigin.LOCAL,
            scope_state=ScopeState.EXCLUDED,
        )
        .filter(
            Q(parent__isnull=True)
            | Q(parent__scope_state=ScopeState.ACTIVE)
            | Q(parent__scope_role=ScopeRole.CONTEXT)
        )
        .select_related("parent")
        .order_by("sort_order_snapshot", "id")
    )
    descriptions = (
        SpecificationValue.objects.filter(
            inspection_node__inspection=inspection,
            scope_origin=ScopeOrigin.LOCAL,
            scope_state=ScopeState.EXCLUDED,
        )
        .filter(
            Q(inspection_node__scope_state=ScopeState.ACTIVE)
            | Q(inspection_node__scope_role=ScopeRole.CONTEXT)
        )
        .select_related("inspection_node")
        .order_by("inspection_node_id", "sort_order_snapshot", "id")
    )
    items = (
        InspectionItemResult.objects.filter(
            inspection_node__inspection=inspection,
            scope_origin=ScopeOrigin.LOCAL,
            scope_state=ScopeState.EXCLUDED,
        )
        .filter(
            Q(inspection_node__scope_state=ScopeState.ACTIVE)
            | Q(inspection_node__scope_role=ScopeRole.CONTEXT)
        )
        .select_related("inspection_node")
        .order_by("inspection_node_id", "sort_order_snapshot", "id")
    )
    return render(
        request,
        "core/local_removed.html",
        {
            "inspection": inspection,
            "nodes": nodes,
            "descriptions": descriptions,
            "items": items,
        },
    )


@login_required
def local_node_restore(request, inspection_pk, node_pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    inspection = _owned_editable_inspection(request, inspection_pk)
    node = _local_node(inspection, node_pk, state=ScopeState.EXCLUDED)
    try:
        restore_local_node(node, request.user)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect("local_removed_content", inspection_pk=inspection.pk)
    messages.success(request, "تمت استعادة الفرع المحلي ومحتواه.")
    return redirect(
        "inspection_node_prepare",
        inspection_pk=inspection.pk,
        node_pk=node.pk,
    )


@login_required
def local_specification_restore(request, inspection_pk, spec_pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    inspection = _owned_editable_inspection(request, inspection_pk)
    spec = _local_specification(inspection, spec_pk, state=ScopeState.EXCLUDED)
    try:
        restore_local_specification(spec, request.user)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect("local_removed_content", inspection_pk=inspection.pk)
    messages.success(request, "تمت استعادة الوصف المحلي.")
    return redirect(
        "inspection_node_prepare",
        inspection_pk=inspection.pk,
        node_pk=spec.inspection_node_id,
    )


@login_required
def local_item_restore(request, inspection_pk, item_pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    inspection = _owned_editable_inspection(request, inspection_pk)
    item = _local_item(inspection, item_pk, state=ScopeState.EXCLUDED)
    try:
        restore_local_item(item, request.user)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect("local_removed_content", inspection_pk=inspection.pk)
    messages.success(request, "تمت استعادة البند المحلي.")
    return redirect(
        "inspection_node_prepare",
        inspection_pk=inspection.pk,
        node_pk=item.inspection_node_id,
    )
