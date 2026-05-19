import json

from django.db import DatabaseError, OperationalError
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .models import VerificationAudit
from .utils import safe_verify


def _extract_audit_fields(presentation: object) -> dict[str, str]:
    if not isinstance(presentation, dict):
        return {"presentation_id": "", "credential_id": "", "issuer": ""}
    credential = presentation.get("verifiableCredential")
    if not isinstance(credential, dict):
        credential = {}
    return {
        "presentation_id": str(presentation.get("id", "")),
        "credential_id": str(credential.get("id", "")),
        "issuer": str(credential.get("issuer", "")),
    }


def _audit_payload(record: VerificationAudit) -> dict:
    return {
        "id": record.id,
        "presentation_id": record.presentation_id,
        "credential_id": record.credential_id,
        "issuer": record.issuer,
        "valid": record.valid,
        "reason": record.reason,
        "disclosed_claims": record.disclosed_claims,
        "created_at": record.created_at.isoformat(),
    }


@csrf_exempt
def verify_presentation(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        return render(request, "verifier_app/audit.html")

    if request.method != "POST":
        return JsonResponse(
            {"valid": False, "reason": "Verifier accepts GET for the audit page and POST for verification."},
            status=405,
        )

    try:
        presentation = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"valid": False, "reason": "Request body must be valid JSON."})

    result = safe_verify(presentation)
    fields = _extract_audit_fields(presentation)
    try:
        VerificationAudit.objects.create(
            presentation_id=fields["presentation_id"],
            credential_id=fields["credential_id"],
            issuer=fields["issuer"],
            valid=bool(result.get("valid")),
            reason=str(result.get("reason", "")),
            disclosed_claims=result.get("disclosed_claims", {}),
        )
    except (DatabaseError, OperationalError):
        result["audit_saved"] = False
        result["audit_reason"] = "Verifier audit table is not ready. Restart the service runner so migrations run."
    return JsonResponse(result)


def audit_events(request: HttpRequest) -> JsonResponse:
    try:
        records = VerificationAudit.objects.order_by("-created_at")[:25]
        return JsonResponse({"ready": True, "audits": [_audit_payload(record) for record in records]})
    except (DatabaseError, OperationalError):
        return JsonResponse(
            {
                "ready": False,
                "audits": [],
                "error": "Verifier audit table is not ready. Stop and restart run_all_services.ps1 so migrations run.",
            }
        )
