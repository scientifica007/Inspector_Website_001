from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .builder_forms import (
    ChecklistItemForm,
    ReferenceForm,
    SpecificationDefinitionForm,
    StructureNodeForm,
)
from .models import (
    ChecklistItem,
    MasterStatus,
    MasterVersion,
    ReferenceVisibility,
    SpecificationDefinition,
    StructureNode,
)
from .services import flatten_nodes, next_reference_number
from .views import is_admin


def admin_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("هذه الصفحة مخصصة للإدارة.")
        return view(request, *args, **kwargs)
    return wrapped


def reference_or_404(pk):
    return get_object_or_404(MasterVersion, pk=pk)


def node_reference_or_404(pk):
    node = get_object_or_404(
        StructureNode.objects.select_related("master_version"),
        pk=pk,
    )
    return node.master_version, node


@admin_required
def builder_home(request):
    references = MasterVersion.objects.all().select_related("owner")
    return render(
        request,
        "builder/home.html",
        {"references": references},
    )


@admin_required
def reference_create(request):
    form = ReferenceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        reference = form.save(commit=False)
        reference.number = next_reference_number()
        reference.visibility = ReferenceVisibility.SHARED
        reference.owner = None
        # Legacy field only: it no longer supersedes any other reference.
        reference.status = MasterStatus.PUBLISHED
        reference.save()
        messages.success(request, "تم إنشاء المرجع المشترك.")
        return redirect("builder_reference", reference_pk=reference.pk)
    return render(
        request,
        "builder/reference_form.html",
        {"form": form, "title": "إنشاء مرجع مشترك"},
    )


@admin_required
def reference_detail(request, reference_pk):
    reference = reference_or_404(reference_pk)
    return render(
        request,
        "builder/reference_detail.html",
        {
            "reference": reference,
            "tree": flatten_nodes(reference),
        },
    )


@admin_required
def reference_edit(request, reference_pk):
    reference = reference_or_404(reference_pk)
    form = ReferenceForm(request.POST or None, instance=reference)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم تحديث اسم المرجع.")
        return redirect("builder_reference", reference_pk=reference.pk)
    return render(
        request,
        "builder/reference_form.html",
        {"form": form, "title": "تعديل المرجع", "reference": reference},
    )


@admin_required
def reference_delete(request, reference_pk):
    if request.method != "POST":
        raise Http404
    reference = reference_or_404(reference_pk)
    name = reference.name
    reference.delete()
    messages.success(
        request,
        f"حُذف المرجع «{name}». الزيارات السابقة وSnapshots الخاصة بها لم تُحذف.",
    )
    return redirect("builder_home")


@admin_required
def node_detail(request, pk):
    reference, node = node_reference_or_404(pk)
    return render(
        request,
        "builder/node_detail.html",
        {
            "reference": reference,
            "node": node,
            "children": node.children.order_by("sort_order", "id"),
            "specifications": node.specifications.order_by("sort_order", "id"),
            "items": node.items.order_by("sort_order", "id"),
        },
    )


@admin_required
def node_create(request, reference_pk):
    reference = reference_or_404(reference_pk)
    parent = None
    parent_id = request.GET.get("parent")
    if parent_id:
        parent = get_object_or_404(
            StructureNode,
            pk=parent_id,
            master_version=reference,
        )
    form = StructureNodeForm(
        request.POST or None,
        reference=reference,
        initial={"parent": parent},
    )
    if request.method == "POST" and form.is_valid():
        node = form.save()
        messages.success(request, "تمت إضافة العنصر.")
        return redirect("builder_node", pk=node.pk)
    return render(
        request,
        "builder/form.html",
        {
            "form": form,
            "title": "إضافة عنصر هيكلي",
            "reference": reference,
        },
    )


@admin_required
def node_edit(request, pk):
    reference, node = node_reference_or_404(pk)
    form = StructureNodeForm(
        request.POST or None,
        instance=node,
        reference=reference,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم تحديث العنصر.")
        return redirect("builder_node", pk=node.pk)
    return render(
        request,
        "builder/form.html",
        {
            "form": form,
            "title": "تعديل العنصر",
            "reference": reference,
            "node": node,
        },
    )


@admin_required
def node_toggle(request, pk):
    if request.method != "POST":
        raise Http404
    _, node = node_reference_or_404(pk)
    node.active = not node.active
    node.save(update_fields=["active"])
    messages.success(request, "تم تحديث حالة العنصر.")
    return redirect("builder_node", pk=node.pk)


@admin_required
def node_delete(request, pk):
    if request.method != "POST":
        raise Http404
    reference, node = node_reference_or_404(pk)
    title = node.title
    node.delete()
    messages.success(request, f"حُذف العنصر «{title}» من المرجع.")
    return redirect("builder_reference", reference_pk=reference.pk)


@admin_required
def specification_create(request, node_pk):
    reference, node = node_reference_or_404(node_pk)
    form = SpecificationDefinitionForm(request.POST or None, node=node)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تمت إضافة الوصف.")
        return redirect("builder_node", pk=node.pk)
    return render(
        request,
        "builder/form.html",
        {
            "form": form,
            "title": "إضافة وصف",
            "reference": reference,
            "node": node,
        },
    )


@admin_required
def specification_edit(request, pk):
    spec = get_object_or_404(
        SpecificationDefinition.objects.select_related("node__master_version"),
        pk=pk,
    )
    reference = spec.node.master_version
    form = SpecificationDefinitionForm(
        request.POST or None,
        instance=spec,
        node=spec.node,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم تحديث الوصف.")
        return redirect("builder_node", pk=spec.node_id)
    return render(
        request,
        "builder/form.html",
        {
            "form": form,
            "title": "تعديل الوصف",
            "reference": reference,
            "node": spec.node,
        },
    )


@admin_required
def specification_toggle(request, pk):
    if request.method != "POST":
        raise Http404
    spec = get_object_or_404(SpecificationDefinition, pk=pk)
    spec.active = not spec.active
    spec.save(update_fields=["active"])
    return redirect("builder_node", pk=spec.node_id)


@admin_required
def specification_delete(request, pk):
    if request.method != "POST":
        raise Http404
    spec = get_object_or_404(SpecificationDefinition, pk=pk)
    node_id = spec.node_id
    title = spec.title
    spec.delete()
    messages.success(request, f"حُذف الوصف «{title}» من المرجع.")
    return redirect("builder_node", pk=node_id)


@admin_required
def item_create(request, node_pk):
    reference, node = node_reference_or_404(node_pk)
    form = ChecklistItemForm(request.POST or None, node=node)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تمت إضافة بند التفتيش.")
        return redirect("builder_node", pk=node.pk)
    return render(
        request,
        "builder/form.html",
        {
            "form": form,
            "title": "إضافة بند تفتيش",
            "reference": reference,
            "node": node,
        },
    )


@admin_required
def item_edit(request, pk):
    item = get_object_or_404(
        ChecklistItem.objects.select_related("node__master_version"),
        pk=pk,
    )
    reference = item.node.master_version
    form = ChecklistItemForm(
        request.POST or None,
        instance=item,
        node=item.node,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم تحديث بند التفتيش.")
        return redirect("builder_node", pk=item.node_id)
    return render(
        request,
        "builder/form.html",
        {
            "form": form,
            "title": "تعديل بند التفتيش",
            "reference": reference,
            "node": item.node,
        },
    )


@admin_required
def item_toggle(request, pk):
    if request.method != "POST":
        raise Http404
    item = get_object_or_404(ChecklistItem, pk=pk)
    item.active = not item.active
    item.save(update_fields=["active"])
    return redirect("builder_node", pk=item.node_id)


@admin_required
def item_delete(request, pk):
    if request.method != "POST":
        raise Http404
    item = get_object_or_404(ChecklistItem, pk=pk)
    node_id = item.node_id
    title = item.title
    item.delete()
    messages.success(request, f"حُذف البند «{title}» من المرجع.")
    return redirect("builder_node", pk=node_id)


@admin_required
def reference_preview(request, reference_pk):
    reference = reference_or_404(reference_pk)
    tree = flatten_nodes(reference, active_only=True)
    return render(
        request,
        "builder/preview.html",
        {"reference": reference, "tree": tree},
    )
