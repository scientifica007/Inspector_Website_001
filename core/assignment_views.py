from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Max
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from .assignment_forms import (
    AssignmentForm,
    AssignmentObligationForm,
    AssignmentRevocationForm,
)
from .assignments import issue_assignment, revoke_assignment
from .builder_views import admin_required
from .models import (
    Assignment,
    AssignmentEntry,
    AssignmentEntryType,
    AssignmentStatus,
    ChecklistItem,
    Inspection,
    InspectionStatus,
    SpecificationDefinition,
    StructureNode,
)
from .services import flatten_nodes
from .views import inspection_for_user, is_admin


def _assignment_for_user(user, pk):
    assignment = get_object_or_404(
        Assignment.objects.select_related(
            "inspection__institution",
            "inspection__inspector",
            "inspection__master_version",
            "created_by",
            "issued_by",
            "revoked_by",
        ),
        pk=pk,
    )
    inspection_for_user(user, assignment.inspection_id)
    if not is_admin(user) and assignment.status == AssignmentStatus.DRAFT:
        raise Http404("التكليف لم يصدر بعد.")
    return assignment


def _draft_assignment_or_404(pk):
    assignment = get_object_or_404(
        Assignment.objects.select_related(
            "inspection__master_version",
            "inspection__institution",
        ),
        pk=pk,
        status=AssignmentStatus.DRAFT,
        inspection__status=InspectionStatus.DRAFT,
    )
    return assignment


def _active_path(node):
    current = node
    reference_id = node.master_version_id
    while current is not None:
        if current.master_version_id != reference_id or not current.active:
            return False
        current = current.parent
    return True


def _target_for_entry(assignment, entry_type, target_id):
    reference = assignment.inspection.master_version
    if reference is None:
        raise Http404("الزيارة لا تحتوي مرجعًا مجمدًا.")

    if entry_type == AssignmentEntryType.BRANCH:
        target = get_object_or_404(
            StructureNode,
            pk=target_id,
            master_version=reference,
            active=True,
        )
        if not _active_path(target):
            raise Http404("المسار المرجعي غير نشط.")
        return target

    if entry_type == AssignmentEntryType.SPECIFICATION:
        target = get_object_or_404(
            SpecificationDefinition,
            pk=target_id,
            node__master_version=reference,
            active=True,
        )
        if not _active_path(target.node):
            raise Http404("المسار المرجعي غير نشط.")
        return target

    if entry_type == AssignmentEntryType.ITEM:
        target = get_object_or_404(
            ChecklistItem,
            pk=target_id,
            node__master_version=reference,
            active=True,
        )
        if not _active_path(target.node):
            raise Http404("المسار المرجعي غير نشط.")
        return target

    raise Http404("نوع عنصر التكليف غير معروف.")


def _next_entry_order(assignment):
    return (assignment.entries.aggregate(value=Max("sort_order"))["value"] or 0) + 10


@login_required
def inspection_assignments(request, inspection_pk):
    inspection = inspection_for_user(request.user, inspection_pk)
    assignments = inspection.assignments.select_related(
        "created_by", "issued_by", "revoked_by"
    )
    if not is_admin(request.user):
        assignments = assignments.exclude(status=AssignmentStatus.DRAFT)

    return render(
        request,
        "assignments/inspection_list.html",
        {
            "inspection": inspection,
            "assignments": assignments,
            "is_admin_user": is_admin(request.user),
            "can_create": (
                is_admin(request.user)
                and inspection.status == InspectionStatus.DRAFT
                and inspection.master_version_id is not None
            ),
        },
    )


@admin_required
def assignment_create(request, inspection_pk):
    inspection = get_object_or_404(
        Inspection.objects.select_related("institution", "master_version"),
        pk=inspection_pk,
    )
    if inspection.status != InspectionStatus.DRAFT:
        raise PermissionDenied("لا يمكن إنشاء تكليف لزيارة مكتملة.")
    if inspection.master_version_id is None:
        raise PermissionDenied("التكليف يتطلب زيارة لها مرجع مجمد.")

    form = AssignmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        assignment = form.save(commit=False)
        assignment.inspection = inspection
        assignment.created_by = request.user
        assignment.save()
        messages.success(
            request,
            "تم إنشاء مسودة التكليف. أضف الالتزامات ثم أصدر التكليف صراحة.",
        )
        return redirect("assignment_detail", pk=assignment.pk)

    return render(
        request,
        "assignments/form.html",
        {
            "form": form,
            "title": "إنشاء تكليف رسمي",
            "inspection": inspection,
        },
    )


@admin_required
def assignment_edit(request, pk):
    assignment = _draft_assignment_or_404(pk)
    form = AssignmentForm(request.POST or None, instance=assignment)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم تحديث مسودة التكليف.")
        return redirect("assignment_detail", pk=assignment.pk)

    return render(
        request,
        "assignments/form.html",
        {
            "form": form,
            "title": "تعديل مسودة التكليف",
            "inspection": assignment.inspection,
            "assignment": assignment,
        },
    )


@login_required
def assignment_detail(request, pk):
    assignment = _assignment_for_user(request.user, pk)
    entries = list(
        assignment.entries.prefetch_related(
            "effects__node",
            "effects__specification",
            "effects__item",
        ).order_by("sort_order", "id")
    )
    selected = {
        AssignmentEntryType.BRANCH: {
            str(entry.stable_id)
            for entry in entries
            if entry.entry_type == AssignmentEntryType.BRANCH
        },
        AssignmentEntryType.SPECIFICATION: {
            str(entry.stable_id)
            for entry in entries
            if entry.entry_type == AssignmentEntryType.SPECIFICATION
        },
        AssignmentEntryType.ITEM: {
            str(entry.stable_id)
            for entry in entries
            if entry.entry_type == AssignmentEntryType.ITEM
        },
    }
    can_manage_draft = (
        is_admin(request.user)
        and assignment.status == AssignmentStatus.DRAFT
        and assignment.inspection.status == InspectionStatus.DRAFT
    )
    can_revoke = (
        is_admin(request.user)
        and assignment.status == AssignmentStatus.ISSUED
        and assignment.inspection.status == InspectionStatus.DRAFT
    )

    return render(
        request,
        "assignments/detail.html",
        {
            "assignment": assignment,
            "inspection": assignment.inspection,
            "entries": entries,
            "tree": (
                flatten_nodes(
                    assignment.inspection.master_version,
                    active_only=True,
                )
                if can_manage_draft
                else []
            ),
            "branch_ids": selected[AssignmentEntryType.BRANCH],
            "spec_ids": selected[AssignmentEntryType.SPECIFICATION],
            "item_ids": selected[AssignmentEntryType.ITEM],
            "can_manage_draft": can_manage_draft,
            "can_revoke": can_revoke,
            "revocation_form": AssignmentRevocationForm(),
            "is_admin_user": is_admin(request.user),
        },
    )


@admin_required
def assignment_entry_add(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    assignment = _draft_assignment_or_404(pk)
    entry_type = request.POST.get("entry_type", "")
    target_id = request.POST.get("target_id")
    target = _target_for_entry(assignment, entry_type, target_id)

    form = AssignmentObligationForm(request.POST)
    if not form.is_valid():
        for error in form.non_field_errors():
            messages.error(request, error)
        return redirect("assignment_detail", pk=assignment.pk)

    entry, created = AssignmentEntry.objects.get_or_create(
        assignment=assignment,
        entry_type=entry_type,
        stable_id=target.stable_id,
        defaults={
            "label_snapshot": target.title,
            "scope_locked": form.cleaned_data["scope_locked"],
            "completion_required": form.cleaned_data["completion_required"],
            "sort_order": _next_entry_order(assignment),
        },
    )
    if created:
        messages.success(request, "أضيف الالتزام إلى مسودة التكليف.")
    else:
        entry.label_snapshot = target.title
        entry.scope_locked = form.cleaned_data["scope_locked"]
        entry.completion_required = form.cleaned_data["completion_required"]
        entry.save(
            update_fields=[
                "label_snapshot",
                "scope_locked",
                "completion_required",
            ]
        )
        messages.success(request, "تم تحديث التزام العنصر داخل المسودة.")

    return redirect("assignment_detail", pk=assignment.pk)


@admin_required
def assignment_entry_delete(request, pk, entry_pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    assignment = _draft_assignment_or_404(pk)
    entry = get_object_or_404(
        AssignmentEntry,
        pk=entry_pk,
        assignment=assignment,
    )
    entry.delete()
    messages.success(request, "أزيل العنصر من مسودة التكليف.")
    return redirect("assignment_detail", pk=assignment.pk)


@admin_required
def assignment_delete(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    assignment = _draft_assignment_or_404(pk)
    inspection_id = assignment.inspection_id
    assignment.delete()
    messages.success(request, "تم حذف مسودة التكليف.")
    return redirect("inspection_assignments", inspection_pk=inspection_id)


@admin_required
def assignment_issue(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    assignment = _draft_assignment_or_404(pk)
    try:
        issue_assignment(assignment, request.user)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(
            request,
            "صدر التكليف وطبقت التزاماته على نطاق الزيارة.",
        )
    return redirect("assignment_detail", pk=assignment.pk)


@admin_required
def assignment_revoke(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    assignment = get_object_or_404(
        Assignment,
        pk=pk,
        status=AssignmentStatus.ISSUED,
    )
    form = AssignmentRevocationForm(request.POST)
    if not form.is_valid():
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)
        return redirect("assignment_detail", pk=assignment.pk)

    try:
        revoke_assignment(
            assignment,
            request.user,
            form.cleaned_data["reason"],
        )
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(
            request,
            "أُلغي التكليف. بقيت بيانات الزيارة وأعيد حساب القيود الفعالة.",
        )
    return redirect("assignment_detail", pk=assignment.pk)
