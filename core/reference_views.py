from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from .builder_views import admin_required
from .models import (
    MasterStatus,
    MasterVersion,
    ReferenceSubmission,
    ReferenceSubmissionStatus,
    ReferenceVisibility,
)
from .reference_forms import (
    PrivateReferenceCreateForm,
    ReferenceCloneForm,
    ReferenceSubmissionReviewForm,
)
from .reference_library import (
    approve_reference_submission,
    clone_as_private,
    reject_reference_submission,
    submit_private_reference,
    withdraw_submission,
)
from .services import flatten_nodes, next_reference_number, visible_references
from .views import is_admin


def _owned_private_reference(user, pk):
    return get_object_or_404(
        MasterVersion,
        pk=pk,
        visibility=ReferenceVisibility.PRIVATE,
        owner=user,
    )


def _visible_reference(user, pk):
    return get_object_or_404(visible_references(user), pk=pk)


def _flatten_snapshot(snapshot):
    rows = []

    def walk(nodes, depth=0):
        for node in nodes:
            rows.append(
                {
                    "node": node,
                    "depth": depth,
                    "descriptions": node.get("descriptions", []),
                    "items": node.get("items", []),
                }
            )
            walk(node.get("children", []), depth + 1)

    walk(snapshot.get("nodes", []))
    return rows


@login_required
def reference_detail(request, pk):
    reference = _visible_reference(request.user, pk)
    return render(
        request,
        "core/reference_detail.html",
        {
            "reference": reference,
            "tree": flatten_nodes(reference),
            "is_owner": reference.owner_id == request.user.id,
            "is_admin_user": is_admin(request.user),
        },
    )


@login_required
def private_reference_create(request):
    if is_admin(request.user):
        raise PermissionDenied("المراجع الخاصة مخصصة لمساحة المفتش.")
    form = PrivateReferenceCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        reference = MasterVersion.objects.create(
            number=next_reference_number(),
            name=form.cleaned_data["name"].strip(),
            visibility=ReferenceVisibility.PRIVATE,
            owner=request.user,
            status=MasterStatus.DRAFT,
        )
        messages.success(request, "تم إنشاء المرجع الخاص. لا يراه المفتشون الآخرون ولا الإدارة.")
        return redirect("builder_reference", reference_pk=reference.pk)
    return render(
        request,
        "core/private_reference_form.html",
        {"form": form, "title": "مرجع خاص جديد"},
    )


@login_required
def clone_reference_private(request, pk):
    if is_admin(request.user):
        raise PermissionDenied("نسخة المرجع الخاصة مخصصة لمساحة المفتش.")
    source = _visible_reference(request.user, pk)
    form = ReferenceCloneForm(
        request.POST or None,
        initial={"name": f"نسخة من {source.name}"},
    )
    if request.method == "POST" and form.is_valid():
        clone = clone_as_private(
            source,
            request.user,
            name=form.cleaned_data["name"].strip(),
        )
        messages.success(request, "أُنشئت نسخة خاصة مستقلة في مكتبة مراجعك.")
        return redirect("builder_reference", reference_pk=clone.pk)
    return render(
        request,
        "core/private_reference_form.html",
        {
            "form": form,
            "title": "نسخ المرجع إلى مكتبتي الخاصة",
            "source": source,
        },
    )


@login_required
def submit_reference(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    reference = _owned_private_reference(request.user, pk)
    try:
        submission, created = submit_private_reference(reference, request.user)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(
            request,
            "أُرسلت Snapshot ثابتة من المرجع إلى الإدارة للمراجعة."
            if created
            else "هذا المرجع لديه اقتراح قيد المراجعة بالفعل.",
        )
    return redirect("builder_reference", reference_pk=reference.pk)


@login_required
def my_reference_submissions(request):
    submissions = ReferenceSubmission.objects.filter(
        submitted_by=request.user
    ).select_related("source_reference", "resulting_reference", "resolved_by")
    return render(
        request,
        "core/reference_submission_mine.html",
        {"submissions": submissions},
    )


@login_required
def withdraw_reference_submission(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    submission = get_object_or_404(
        ReferenceSubmission,
        pk=pk,
        submitted_by=request.user,
    )
    try:
        _, changed = withdraw_submission(submission, request.user)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(
            request,
            "تم سحب الاقتراح." if changed else "سبق حسم هذا الاقتراح.",
        )
    return redirect("my_reference_submissions")


@admin_required
def reference_submission_list(request):
    status = request.GET.get("status", ReferenceSubmissionStatus.PENDING)
    if status not in set(ReferenceSubmissionStatus.values):
        status = ReferenceSubmissionStatus.PENDING
    submissions = ReferenceSubmission.objects.filter(status=status).select_related(
        "submitted_by",
        "resulting_reference",
        "resolved_by",
    )
    return render(
        request,
        "governance/reference_submission_list.html",
        {
            "submissions": submissions,
            "selected_status": status,
            "status_choices": ReferenceSubmissionStatus.choices,
        },
    )


@admin_required
def reference_submission_detail(request, pk):
    submission = get_object_or_404(
        ReferenceSubmission.objects.select_related(
            "submitted_by",
            "resolved_by",
            "resulting_reference",
        ),
        pk=pk,
    )
    form = ReferenceSubmissionReviewForm(
        request.POST or None,
        initial={"shared_name": submission.source_name_snapshot},
    )

    if request.method == "POST" and submission.status == ReferenceSubmissionStatus.PENDING:
        action = request.POST.get("action")
        if action == "approve" and form.is_valid():
            _, changed = approve_reference_submission(
                submission,
                request.user,
                shared_name=form.cleaned_data["shared_name"].strip(),
                note=form.cleaned_data["resolution_note"],
            )
            messages.success(
                request,
                "تم اعتماد Snapshot كمرجع مشترك مستقل."
                if changed
                else "سبق حسم الاقتراح.",
            )
            return redirect("reference_submission_detail", pk=submission.pk)
        if action == "reject":
            note = request.POST.get("resolution_note", "").strip()
            _, changed = reject_reference_submission(
                submission,
                request.user,
                note=note,
            )
            messages.success(
                request,
                "تم رفض التعميم؛ المرجع الخاص لدى المفتش لم يتغير."
                if changed
                else "سبق حسم الاقتراح.",
            )
            return redirect("reference_submission_detail", pk=submission.pk)
        if action not in {"approve", "reject"}:
            form.add_error(None, "إجراء غير معروف.")

    submission.refresh_from_db()
    return render(
        request,
        "governance/reference_submission_detail.html",
        {
            "submission": submission,
            "form": form,
            "snapshot_rows": _flatten_snapshot(submission.snapshot or {}),
        },
    )
