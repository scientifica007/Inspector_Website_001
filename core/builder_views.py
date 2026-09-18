from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .builder_forms import ChecklistItemForm, SpecificationDefinitionForm, StructureNodeForm
from .models import ChecklistItem, MasterStatus, SpecificationDefinition, StructureNode
from .services import create_draft_from_latest_published, flatten_nodes, latest_draft
from .views import is_admin

def admin_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("هذه الصفحة مخصصة للإدارة.")
        return view(request, *args, **kwargs)
    return wrapped

def require_draft():
    draft = latest_draft()
    if draft is None:
        raise Http404("لا توجد مسودة.")
    return draft

@admin_required
def builder_home(request):
    draft = latest_draft()
    tree = flatten_nodes(draft) if draft else []
    return render(request, "builder/home.html", {"draft": draft, "tree": tree})

@admin_required
def draft_create(request):
    if request.method != "POST":
        raise Http404
    draft, created = create_draft_from_latest_published()
    messages.success(
        request,
        f"تم إنشاء المسودة v{draft.number}." if created else f"المسودة v{draft.number} موجودة بالفعل.",
    )
    return redirect("builder_home")

def draft_node_or_404(pk):
    draft = require_draft()
    return draft, get_object_or_404(StructureNode, pk=pk, master_version=draft)

@admin_required
def node_detail(request, pk):
    draft, node = draft_node_or_404(pk)
    return render(
        request,
        "builder/node_detail.html",
        {
            "draft": draft,
            "node": node,
            "children": node.children.order_by("sort_order", "id"),
            "specifications": node.specifications.order_by("sort_order", "id"),
            "items": node.items.order_by("sort_order", "id"),
        },
    )

@admin_required
def node_create(request):
    draft = require_draft()
    parent = None
    parent_id = request.GET.get("parent")
    if parent_id:
        parent = get_object_or_404(StructureNode, pk=parent_id, master_version=draft)
    form = StructureNodeForm(request.POST or None, draft=draft, initial={"parent": parent})
    if request.method == "POST" and form.is_valid():
        node = form.save()
        messages.success(request, "تمت إضافة العنصر.")
        return redirect("builder_node", pk=node.pk)
    return render(request, "builder/form.html", {"form": form, "title": "إضافة عنصر هيكلي", "draft": draft})

@admin_required
def node_edit(request, pk):
    draft, node = draft_node_or_404(pk)
    form = StructureNodeForm(request.POST or None, instance=node, draft=draft)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم تحديث العنصر.")
        return redirect("builder_node", pk=node.pk)
    return render(request, "builder/form.html", {"form": form, "title": "تعديل العنصر", "draft": draft})

@admin_required
def node_toggle(request, pk):
    if request.method != "POST":
        raise Http404
    draft, node = draft_node_or_404(pk)
    node.active = not node.active
    node.save(update_fields=["active"])
    messages.success(request, "تم تحديث حالة العنصر.")
    return redirect("builder_node", pk=node.pk)

@admin_required
def specification_create(request, node_pk):
    draft, node = draft_node_or_404(node_pk)
    form = SpecificationDefinitionForm(request.POST or None, node=node)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تمت إضافة المواصفة.")
        return redirect("builder_node", pk=node.pk)
    return render(request, "builder/form.html", {"form": form, "title": "إضافة مواصفة", "draft": draft, "node": node})

@admin_required
def specification_edit(request, pk):
    draft = require_draft()
    spec = get_object_or_404(
        SpecificationDefinition.objects.select_related("node__master_version"),
        pk=pk,
        node__master_version=draft,
    )
    form = SpecificationDefinitionForm(request.POST or None, instance=spec, node=spec.node)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم تحديث المواصفة.")
        return redirect("builder_node", pk=spec.node_id)
    return render(request, "builder/form.html", {"form": form, "title": "تعديل المواصفة", "draft": draft, "node": spec.node})

@admin_required
def specification_toggle(request, pk):
    if request.method != "POST":
        raise Http404
    draft = require_draft()
    spec = get_object_or_404(SpecificationDefinition, pk=pk, node__master_version=draft)
    spec.active = not spec.active
    spec.save(update_fields=["active"])
    return redirect("builder_node", pk=spec.node_id)

@admin_required
def item_create(request, node_pk):
    draft, node = draft_node_or_404(node_pk)
    form = ChecklistItemForm(request.POST or None, node=node)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تمت إضافة بند التفتيش.")
        return redirect("builder_node", pk=node.pk)
    return render(request, "builder/form.html", {"form": form, "title": "إضافة بند تفتيش", "draft": draft, "node": node})

@admin_required
def item_edit(request, pk):
    draft = require_draft()
    item = get_object_or_404(
        ChecklistItem.objects.select_related("node__master_version"),
        pk=pk,
        node__master_version=draft,
    )
    form = ChecklistItemForm(request.POST or None, instance=item, node=item.node)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم تحديث بند التفتيش.")
        return redirect("builder_node", pk=item.node_id)
    return render(request, "builder/form.html", {"form": form, "title": "تعديل بند التفتيش", "draft": draft, "node": item.node})

@admin_required
def item_toggle(request, pk):
    if request.method != "POST":
        raise Http404
    draft = require_draft()
    item = get_object_or_404(ChecklistItem, pk=pk, node__master_version=draft)
    item.active = not item.active
    item.save(update_fields=["active"])
    return redirect("builder_node", pk=item.node_id)

@admin_required
def draft_preview(request):
    draft = require_draft()
    tree = flatten_nodes(draft, active_only=True)
    return render(request, "builder/preview.html", {"draft": draft, "tree": tree})
