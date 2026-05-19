import json

from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import WalletCredential
from .redaction import build_selective_presentation, validate_credential_structure


def _json_body(request: HttpRequest) -> dict:
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON.") from exc
    if not isinstance(body, dict):
        raise ValueError("Request JSON must be an object.")
    return body


@require_GET
def wallet_ui(request: HttpRequest):
    return render(request, "holder_app/wallet.html")


@require_GET
def list_credentials(request: HttpRequest) -> JsonResponse:
    records = WalletCredential.objects.order_by("-created_at")
    return JsonResponse(
        {
            "credentials": [
                {
                    "wallet_id": record.id,
                    "credential_id": record.credential_id,
                    "issuer": record.issuer,
                    "created_at": record.created_at.isoformat(),
                    "credential": record.credential,
                }
                for record in records
            ]
        }
    )


@csrf_exempt
@require_POST
def receive_credential(request: HttpRequest) -> JsonResponse:
    try:
        credential = _json_body(request)
        validate_credential_structure(credential)
        record = WalletCredential.objects.create(
            credential=credential,
            issuer=str(credential["issuer"]),
            credential_id=str(credential["id"]),
        )
        return JsonResponse(
            {
                "received": True,
                "wallet_id": record.id,
                "credential_id": record.credential_id,
            },
            status=201,
        )
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@csrf_exempt
@require_POST
def generate_presentation(request: HttpRequest) -> JsonResponse:
    try:
        body = _json_body(request)
        wallet_id = body.get("wallet_id")
        disclosed_keys = body.get("disclosed_keys")
        if not isinstance(wallet_id, int):
            raise ValueError("wallet_id must be an integer.")
        if not isinstance(disclosed_keys, list) or not all(isinstance(item, str) for item in disclosed_keys):
            raise ValueError("disclosed_keys must be an array of strings.")

        record = WalletCredential.objects.get(id=wallet_id)
        presentation = build_selective_presentation(record.credential, disclosed_keys)
        return JsonResponse(presentation)
    except WalletCredential.DoesNotExist:
        return JsonResponse({"error": "Credential was not found in the wallet."}, status=404)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
