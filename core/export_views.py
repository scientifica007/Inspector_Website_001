import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.http import require_GET

from .exporting import build_inspection_export
from .views import inspection_for_user

@login_required
@require_GET
def inspection_export(request, pk):
    inspection = inspection_for_user(request.user, pk)
    payload = build_inspection_export(inspection)
    body = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        separators=(",", ": "),
    ) + "\n"
    response = HttpResponse(body, content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="inspection-{inspection.pk}-{inspection.visit_date.isoformat()}.json"'
    )
    return response
