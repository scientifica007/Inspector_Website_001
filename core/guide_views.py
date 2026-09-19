from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Max
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from .builder_views import admin_required
from .guide_forms import GuideCreateForm, GuideEditForm
from .guides import apply_guide, compatible_guides
from .models import (
    ChecklistItem,
    Guide,
    GuideEntry,
    GuideEntryType,
    InspectionStatus,
    ReferenceVisibility,
    SpecificationDefinition,
    StructureNode,
)
from .services import flatten_nodes
from .views import can_edit_inspection, inspection_for_user


def _guide_or_404(pk):
    return get_object_or_404(
        Guide.objects.select_related("reference", "created_by"),
        pk=pk,
        reference__visibility=ReferenceVisibility.SHARED,
    )


def _next_entry_order(guide):
    return (guide.entries.aggregate(value=Max("sort_order"))["value"] or 0) + 10


def _active_path(node):
    current = node
    while current is not None:
        if not current.active or current.master_version_id != node.master_version_id:
            return False
        current = current.parent
    return True


def _entry_target(guide, entry_type, target_id):
    if entry_type == GuideEntryType.BRANCH:
        target = get_object_or_404(
            StructureNode,
            pk=target_id,
            master_version=guide.reference,
            active=True,
        )
        if not _active_path(target):
            raise Http404("المسار المرجعي غير نشط.")
        return target
    if entry_type == GuideEntryType.SPECIFICATION:
        target = get_object_or_404(
            SpecificationDefinition,
            pk=target_id,
            node__master_version=guide.reference,
            active=True,
        )
        if not _active_path(target.node):
            raise Http404("المسار المرجعي غير نشط.")
        return target
    if entry_type == GuideEntryType.ITEM:
        target = get_object_or_404(
            ChecklistItem,
            pk=target_id,
            node__master_version=guide.reference,
            active=True,
        )
        if not _active_path(target.node):
            raise Http404("المسار المرجعي غير نشط.")
        return target
    raise Http404("نوع عنصر الدليل غير معروف.")


@admin_required
def guide_list(request):
    guides = Guide.objects.select_related("reference", "created_by").order_by(
        "name", "id"
    )
    return render(request, "guides/admin_list.html", {"guides": guides})


@admin_required
def guide_create(request):
    form = GuideCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        guide = form.save(commit=False)
        guide.created_by = request.user
        guide.save()
        messages.success(request, "تم إنشاء الدليل. أضف الآن العناصر المقترحة.")
        return redirect("guide_detail", pk=guide.pk)
    return render(
        request,
        "guides/form.html",
        {"form": form, "title": "إنشاء دليل"},
    )


@admin_required
def guide_edit(request, pk):
    guide = _guide_or_404(pk)
    form = GuideEditForm(request.POST or None, instance=guide)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم تحديث الدليل.")
        return redirect("guide_detail", pk=guide.pk)
    return render(
        request,
        "guides/form.html",
        {"form": form, "title": "تعديل الدليل", "guide": guide},
    )


@admin_required
def guide_detail(request, pk):
    guide = _guide_or_404(pk)
    entries = list(guide.entries.all().order_by("sort_order", "id"))
    selected = {
        GuideEntryType.BRANCH: {
            str(entry.stable_id)
            for entry in entries
            if entry.entry_type == GuideEntryType.BRANCH
        },
        GuideEntryType.SPECIFICATION: {
            str(entry.stable_id)
            for entry in entries
            if entry.entry_type == GuideEntryType.SPECIFICATION
        },
        GuideEntryType.ITEM: {
            str(entry.stable_id)
            for entry in entries
            if entry.entry_type == GuideEntryType.ITEM
        },
    }
    return render(
        request,
        "guides/admin_detail.html",
        {
            "guide": guide,
            "tree": flatten_nodes(guide.reference, active_only=True),
            "entries": entries,
            "branch_ids": selected[GuideEntryType.BRANCH],
            "spec_ids": selected[GuideEntryType.SPECIFICATION],
            "item_ids": selected[GuideEntryType.ITEM],
        },
    )


@admin_required
def guide_entry_add(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    guide = _guide_or_404(pk)
    entry_type = request.POST.get("entry_type", "")
    target_id = request.POST.get("target_id")
    target = _entry_target(guide, entry_type, target_id)

    entry, created = GuideEntry.objects.get_or_create(
        guide=guide,
        entry_type=entry_type,
        stable_id=target.stable_id,
        defaults={
            "label_snapshot": target.title,
            "sort_order": _next_entry_order(guide),
        },
    )
    messages.success(
        request,
        "أضيف العنصر إلى الدليل." if created else "العنصر موجود في الدليل أصلًا.",
    )
    return redirect("guide_detail", pk=guide.pk)


@admin_required
def guide_entry_delete(request, pk, entry_pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    guide = _guide_or_404(pk)
    entry = get_object_or_404(GuideEntry, pk=entry_pk, guide=guide)
    entry.delete()
    messages.success(request, "أزيل العنصر من الدليل.")
    return redirect("guide_detail", pk=guide.pk)


@admin_required
def guide_delete(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    guide = _guide_or_404(pk)
    name = guide.name
    guide.delete()
    messages.success(
        request,
        f"حُذف الدليل «{name}». الزيارات التي سبق أن طبقته لم تتغير.",
    )
    return redirect("guide_list")


@login_required
def inspection_guides(request, pk):
    inspection = inspection_for_user(request.user, pk)
    guides = list(compatible_guides(inspection).select_related("reference"))
    applications = list(
        inspection.guide_applications.select_related("guide", "applied_by").all()
    )
    applied_ids = {
        application.guide_id
        for application in applications
        if application.guide_id is not None
    }
    return render(
        request,
        "guides/inspection_guides.html",
        {
            "inspection": inspection,
            "guides": guides,
            "applications": applications,
            "applied_ids": applied_ids,
            "can_edit": can_edit_inspection(request.user, inspection),
        },
    )


@login_required
def apply_inspection_guide(request, pk, guide_pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    inspection = inspection_for_user(request.user, pk)
    if not can_edit_inspection(request.user, inspection):
        raise PermissionDenied("هذه الزيارة للقراءة فقط.")

    guide = get_object_or_404(
        compatible_guides(inspection),
        pk=guide_pk,
    )
    try:
        application, created = apply_guide(inspection, guide, request.user)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        if created:
            message = (
                f"طُبق الدليل: {application.applied_count} اقتراحًا متوافقًا."
            )
            if application.skipped_count:
                message += (
                    f" تعذر العثور على {application.skipped_count} اقتراحًا "
                    "في لقطة هذه الزيارة."
                )
            messages.success(request, message)
        else:
            messages.info(
                request,
                "سبق تطبيق هذا الدليل على الزيارة؛ لم تُكرر أي عناصر.",
            )

    return redirect("inspection_guides", pk=inspection.pk)
