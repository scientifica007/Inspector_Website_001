from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .forms import InspectionCreateForm, InstitutionForm
from .models import (
    Inspection,
    Institution,
    InstitutionVerificationStatus,
    MasterStatus,
    MasterVersion,
    Proposal,
    ProposalType,
    Role,
)

def health(request):
    return JsonResponse({"status": "ok"})

def is_admin(user):
    if user.is_superuser:
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and profile.role == Role.ADMIN)

def visible_institutions(user):
    query = Institution.objects.filter(active=True)
    if is_admin(user):
        return query
    return query.filter(
        Q(verification_status=InstitutionVerificationStatus.VERIFIED) | Q(created_by=user)
    )

@login_required
def dashboard(request):
    inspections = Inspection.objects.select_related("institution", "master_version")
    if not is_admin(request.user):
        inspections = inspections.filter(inspector=request.user)
    return render(request, "core/dashboard.html", {"inspections": inspections})

@login_required
def institution_list(request):
    return render(
        request,
        "core/institution_list.html",
        {"institutions": visible_institutions(request.user)},
    )

@login_required
def institution_create(request):
    form = InstitutionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        institution = form.save(commit=False)
        institution.created_by = request.user
        admin_user = is_admin(request.user)
        institution.verification_status = (
            InstitutionVerificationStatus.VERIFIED
            if admin_user
            else InstitutionVerificationStatus.PENDING
        )
        institution.save()

        if not admin_user:
            Proposal.objects.create(
                proposal_type=ProposalType.INSTITUTION,
                proposed_by=request.user,
                payload={
                    "institution_id": institution.id,
                    "name": institution.name,
                    "institution_type": institution.institution_type,
                    "commune": institution.commune,
                },
            )
            messages.success(
                request,
                "أضيفت المؤسسة لعملك وأرسلت إلى الإدارة للمراجعة قبل تعميمها.",
            )
        else:
            messages.success(request, "أضيفت المؤسسة واعتمدت.")
        return redirect("institution_list")
    return render(request, "core/institution_form.html", {"form": form})

@login_required
def inspection_create(request):
    master = MasterVersion.objects.filter(status=MasterStatus.PUBLISHED).order_by("-number").first()
    institutions = visible_institutions(request.user)
    if master is None:
        return render(
            request,
            "core/inspection_form.html",
            {"form": None, "master_missing": True},
            status=409 if request.method == "POST" else 200,
        )

    form = InspectionCreateForm(request.POST or None, institutions=institutions)
    if request.method == "POST" and form.is_valid():
        inspection = form.save(commit=False)
        inspection.inspector = request.user
        inspection.master_version = master
        inspection.save()
        messages.success(request, "أنشئت مسودة الزيارة.")
        return redirect("dashboard")

    return render(
        request,
        "core/inspection_form.html",
        {"form": form, "master_missing": False, "master": master},
    )
