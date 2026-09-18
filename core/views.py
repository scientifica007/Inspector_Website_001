from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from .models import Inspection, Role

def health(request):
    return JsonResponse({"status": "ok"})

@login_required
def dashboard(request):
    role = getattr(getattr(request.user, "profile", None), "role", Role.INSPECTOR)
    inspections = Inspection.objects.select_related("institution", "master_version")
    if not request.user.is_superuser and role != Role.ADMIN:
        inspections = inspections.filter(inspector=request.user)
    return render(
        request,
        "core/dashboard.html",
        {"inspections": inspections.order_by("-visit_date", "-id")},
    )
