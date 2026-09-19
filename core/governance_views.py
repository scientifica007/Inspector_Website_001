from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .builder_views import admin_required
from .governance import (
    approve_proposal,
    merge_institution_proposal,
    publish_draft,
    reject_proposal,
)
from .governance_forms import ProposalModerationForm, PublishConfirmationForm
from .models import Proposal, ProposalStatus, ProposalType
from .services import latest_draft

@admin_required
def proposal_list(request):
    status = request.GET.get("status", ProposalStatus.PENDING)
    valid_statuses = set(ProposalStatus.values)
    if status not in valid_statuses:
        status = ProposalStatus.PENDING
    proposals = (
        Proposal.objects.select_related("proposed_by", "source_inspection__institution")
        .filter(status=status, proposal_type=ProposalType.INSTITUTION)
        .order_by("-created_at", "-id")
    )
    return render(
        request,
        "governance/proposal_list.html",
        {
            "proposals": proposals,
            "selected_status": status,
            "status_choices": ProposalStatus.choices,
        },
    )

@admin_required
def proposal_detail(request, pk):
    proposal = get_object_or_404(
        Proposal.objects.select_related(
            "proposed_by",
            "source_inspection__institution",
            "resolved_by",
        ),
        pk=pk,
        proposal_type=ProposalType.INSTITUTION,
    )
    form = ProposalModerationForm(request.POST or None, proposal=proposal)

    if request.method == "POST":
        action = request.POST.get("action")
        note = request.POST.get("resolution_note", "").strip()
        try:
            if action == "reject":
                _, changed = reject_proposal(proposal, request.user, note)
                messages.success(
                    request,
                    "تم رفض الاقتراح." if changed else "سبق حسم هذا الاقتراح.",
                )
                return redirect("proposal_detail", pk=proposal.pk)

            if action == "merge":
                if proposal.proposal_type != ProposalType.INSTITUTION:
                    form.add_error(None, "الدمج متاح لاقتراحات المؤسسات فقط.")
                elif form.is_valid():
                    target = form.cleaned_data.get("merge_target")
                    if target is None:
                        form.add_error("merge_target", "اختر المؤسسة المعتمدة المراد الدمج معها.")
                    else:
                        _, changed = merge_institution_proposal(
                            proposal, request.user, target, form.cleaned_data["resolution_note"]
                        )
                        messages.success(
                            request,
                            "تم دمج الاقتراح." if changed else "سبق حسم هذا الاقتراح.",
                        )
                        return redirect("proposal_detail", pk=proposal.pk)

            elif action == "approve":
                if form.is_valid():
                    _, changed = approve_proposal(
                        proposal,
                        request.user,
                        form.updated_payload(),
                        form.cleaned_data["resolution_note"],
                    )
                    messages.success(
                        request,
                        "تم اعتماد اقتراح المؤسسة."
                        if changed
                        else "سبق حسم هذا الاقتراح.",
                    )
                    return redirect("proposal_detail", pk=proposal.pk)
            elif action not in {"merge", "approve", "reject"}:
                form.add_error(None, "إجراء غير معروف.")

        except ValidationError as exc:
            form.add_error(None, " ".join(exc.messages))

        proposal.refresh_from_db()

    return render(
        request,
        "governance/proposal_detail.html",
        {"proposal": proposal, "form": form},
    )

@admin_required
def publish_master(request):
    draft = latest_draft()
    if draft is None:
        raise Http404("لا توجد مسودة للنشر.")

    form = PublishConfirmationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            published = publish_draft(draft)
        except ValidationError as exc:
            form.add_error(None, " ".join(exc.messages))
        else:
            messages.success(request, f"تم نشر المرجع v{published.number}.")
            return redirect("builder_home")

    pending_count = Proposal.objects.filter(status=ProposalStatus.PENDING).count()
    return render(
        request,
        "governance/publish_confirm.html",
        {"draft": draft, "form": form, "pending_count": pending_count},
    )
