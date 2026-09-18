from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import InspectionCreateForm, InstitutionForm
from .inspection_forms import (
    InspectionCompletionForm,
    InspectionGeneralForm,
    InspectionNodeEntryForm,
)
from .models import (
    ChecklistItem,
    Inspection,
    InspectionItemResult,
    InspectionNode,
    InspectionStatus,
    Institution,
    InstitutionVerificationStatus,
    MasterStatus,
    MasterVersion,
    Proposal,
    ProposalType,
    ResultStatus,
    Role,
    ScopeRole,
    ScopeState,
    SpecificationDefinition,
    SpecificationValue,
    StructureNode,
)
from .services import (
    active_item_results,
    add_scope_branch,
    add_scope_item,
    add_scope_specification,
    exclude_scope_item,
    exclude_scope_node,
    exclude_scope_specification,
    flatten_inspection_nodes,
    incomplete_required_scope_count,
    scope_reference_rows,
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
        Q(verification_status=InstitutionVerificationStatus.VERIFIED)
        | Q(
            created_by=user,
            verification_status=InstitutionVerificationStatus.PENDING,
        )
    )

def inspection_for_user(user, pk):
    query = Inspection.objects.select_related("institution", "master_version", "inspector")
    if not is_admin(user):
        query = query.filter(inspector=user)
    return get_object_or_404(query, pk=pk)

def can_edit_inspection(user, inspection):
    return (
        inspection.inspector_id == user.id
        and inspection.status == InspectionStatus.DRAFT
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
                source_local_id=institution.id,
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
        with transaction.atomic():
            inspection = form.save(commit=False)
            inspection.inspector = request.user
            inspection.master_version = master
            inspection.save()
        messages.success(
            request,
            "أنشئت مسودة الزيارة وربطت بالمرجع المنشور. حدّد نطاق الزيارة حسب الحاجة.",
        )
        return redirect("inspection_detail", pk=inspection.pk)

    return render(
        request,
        "core/inspection_form.html",
        {"form": form, "master_missing": False, "master": master},
    )

@login_required
def inspection_detail(request, pk):
    inspection = inspection_for_user(request.user, pk)
    tree = flatten_inspection_nodes(inspection, active_only=True)
    item_query = active_item_results(inspection)
    total = item_query.count()
    resolved = item_query.exclude(status=ResultStatus.UNCHECKED).count()
    progress = round((resolved / total) * 100) if total else 0
    return render(
        request,
        "core/inspection_detail.html",
        {
            "inspection": inspection,
            "tree": tree,
            "total_items": total,
            "resolved_items": resolved,
            "progress": progress,
            "can_edit": can_edit_inspection(request.user, inspection),
        },
    )

@login_required
def inspection_scope(request, pk):
    inspection = inspection_for_user(request.user, pk)
    editable = can_edit_inspection(request.user, inspection)

    if request.method == "POST":
        if not editable:
            raise PermissionDenied("لا تملك صلاحية تعديل نطاق هذه الزيارة.")

        action = request.POST.get("action", "")
        try:
            if action == "add_branch":
                source = get_object_or_404(
                    StructureNode,
                    pk=request.POST.get("source_node_id"),
                    master_version=inspection.master_version,
                )
                add_scope_branch(inspection, source)
                messages.success(request, "أضيف الفرع ومحتواه النشط إلى نطاق الزيارة.")

            elif action == "add_spec":
                source = get_object_or_404(
                    SpecificationDefinition.objects.select_related("node"),
                    pk=request.POST.get("source_spec_id"),
                    node__master_version=inspection.master_version,
                )
                add_scope_specification(inspection, source)
                messages.success(request, "أضيفت المواصفة إلى نطاق الزيارة.")

            elif action == "add_item":
                source = get_object_or_404(
                    ChecklistItem.objects.select_related("node"),
                    pk=request.POST.get("source_item_id"),
                    node__master_version=inspection.master_version,
                )
                add_scope_item(inspection, source)
                messages.success(request, "أضيف البند إلى نطاق الزيارة.")

            elif action == "exclude_node":
                snapshot = get_object_or_404(
                    InspectionNode,
                    pk=request.POST.get("snapshot_id"),
                    inspection=inspection,
                )
                exclude_scope_node(snapshot)
                messages.success(request, "أخرج الفرع من النطاق مع الاحتفاظ ببياناته.")

            elif action == "restore_node":
                snapshot = get_object_or_404(
                    InspectionNode.objects.select_related("source_node"),
                    pk=request.POST.get("snapshot_id"),
                    inspection=inspection,
                    source_node__isnull=False,
                )
                add_scope_branch(inspection, snapshot.source_node)
                messages.success(request, "أعيد الفرع إلى النطاق واستعيدت بياناته السابقة.")

            elif action == "exclude_spec":
                value = get_object_or_404(
                    SpecificationValue,
                    pk=request.POST.get("snapshot_id"),
                    inspection_node__inspection=inspection,
                )
                exclude_scope_specification(value)
                messages.success(request, "أخرجت المواصفة من النطاق مع الاحتفاظ بقيمتها.")

            elif action == "restore_spec":
                value = get_object_or_404(
                    SpecificationValue.objects.select_related("source_specification__node"),
                    pk=request.POST.get("snapshot_id"),
                    inspection_node__inspection=inspection,
                    source_specification__isnull=False,
                )
                add_scope_specification(inspection, value.source_specification)
                messages.success(request, "أعيدت المواصفة إلى النطاق بقيمتها السابقة.")

            elif action == "exclude_item":
                result = get_object_or_404(
                    InspectionItemResult,
                    pk=request.POST.get("snapshot_id"),
                    inspection_node__inspection=inspection,
                )
                exclude_scope_item(result)
                messages.success(request, "أخرج البند من النطاق مع الاحتفاظ بنتيجته.")

            elif action == "restore_item":
                result = get_object_or_404(
                    InspectionItemResult.objects.select_related("source_item__node"),
                    pk=request.POST.get("snapshot_id"),
                    inspection_node__inspection=inspection,
                    source_item__isnull=False,
                )
                add_scope_item(inspection, result.source_item)
                messages.success(request, "أعيد البند إلى النطاق بنتيجته السابقة.")

            else:
                messages.error(request, "إجراء نطاق غير معروف.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))

        return redirect("inspection_scope", pk=inspection.pk)

    return render(
        request,
        "core/inspection_scope.html",
        {
            "inspection": inspection,
            "rows": scope_reference_rows(inspection),
            "can_edit": editable,
            "scope_state": ScopeState,
            "scope_role": ScopeRole,
        },
    )

@login_required
def inspection_node(request, inspection_pk, node_pk):
    inspection = inspection_for_user(request.user, inspection_pk)
    node = get_object_or_404(
        inspection.inspection_nodes.all(),
        pk=node_pk,
    )
    if node.scope_state != ScopeState.ACTIVE or node.scope_role != ScopeRole.SELECTED:
        raise Http404("هذا العنصر ليس مجالًا نشطًا قابلًا للتعبئة في نطاق الزيارة.")

    editable = can_edit_inspection(request.user, inspection)

    if request.method == "POST" and not editable:
        if inspection.status == InspectionStatus.COMPLETED:
            return HttpResponse("الزيارة مكتملة ولا يمكن تعديلها.", status=409)
        raise PermissionDenied("لا تملك صلاحية تعديل هذه الزيارة.")

    form = InspectionNodeEntryForm(
        request.POST or None,
        node=node,
        readonly=not editable,
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            form.save()
        messages.success(request, "تم حفظ بيانات هذا المجال.")
        return redirect("inspection_node", inspection_pk=inspection.pk, node_pk=node.pk)

    return render(
        request,
        "core/inspection_node.html",
        {
            "inspection": inspection,
            "node": node,
            "form": form,
            "specification_blocks": form.specification_blocks,
            "item_blocks": form.item_blocks,
            "can_edit": editable,
        },
    )

@login_required
def inspection_general(request, pk):
    inspection = inspection_for_user(request.user, pk)
    editable = can_edit_inspection(request.user, inspection)

    if request.method == "POST" and not editable:
        if inspection.status == InspectionStatus.COMPLETED:
            return HttpResponse("الزيارة مكتملة ولا يمكن تعديلها.", status=409)
        raise PermissionDenied("لا تملك صلاحية تعديل هذه الزيارة.")

    form = InspectionGeneralForm(
        request.POST or None,
        instance=inspection,
        readonly=not editable,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم حفظ المعاينات والتوصيات العامة.")
        return redirect("inspection_detail", pk=inspection.pk)

    return render(
        request,
        "core/inspection_general.html",
        {"inspection": inspection, "form": form, "can_edit": editable},
    )

@login_required
def inspection_complete(request, pk):
    inspection = inspection_for_user(request.user, pk)
    if inspection.inspector_id != request.user.id:
        raise PermissionDenied("إنهاء الزيارة متاح للمفتش صاحبها فقط.")
    if inspection.status == InspectionStatus.COMPLETED:
        messages.info(request, "هذه الزيارة مكتملة بالفعل.")
        return redirect("inspection_detail", pk=inspection.pk)

    required_missing = incomplete_required_scope_count(inspection)
    form = InspectionCompletionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if required_missing:
            form.add_error(
                None,
                f"لا يمكن إنهاء الزيارة قبل حسم {required_missing} عنصرًا إلزاميًا.",
            )
        else:
            inspection.status = InspectionStatus.COMPLETED
            inspection.save(update_fields=["status", "updated_at"])
            messages.success(request, "تم إنهاء الزيارة. أصبحت البيانات للقراءة فقط.")
            return redirect("inspection_detail", pk=inspection.pk)

    unchecked = active_item_results(inspection).filter(
        status=ResultStatus.UNCHECKED,
    ).count()
    return render(
        request,
        "core/inspection_complete.html",
        {
            "inspection": inspection,
            "form": form,
            "unchecked": unchecked,
            "required_missing": required_missing,
        },
    )
