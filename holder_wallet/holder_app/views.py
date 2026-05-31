import json

from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .crypto import generate_rsa_keypair, public_key_fingerprint
from .models import HolderKeyPair, HolderProfile, WalletCredential
from .registry import HOLDER_ORIGIN, holder_public_url, register_holder_key
from .redaction import build_selective_presentation, validate_credential_structure


def _json_body(request: HttpRequest) -> dict:
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON.") from exc
    if not isinstance(body, dict):
        raise ValueError("Request JSON must be an object.")
    return body


DEFAULT_HOLDERS = [
    {"holder_id": "student_001", "display_name": "Nischal Ghimire", "email": "nischal@example.local"},
    {"holder_id": "student_002", "display_name": "Aarav Sharma", "email": "aarav@example.local"},
    {"holder_id": "student_003", "display_name": "Sita Thapa", "email": "sita@example.local"},
]


def _ensure_holder_key(holder: HolderProfile) -> HolderKeyPair:
    if hasattr(holder, "keypair"):
        return holder.keypair
    private_pem, public_pem = generate_rsa_keypair()
    return HolderKeyPair.objects.create(
        holder=holder,
        key_id="default",
        private_key_pem=private_pem,
        public_key_pem=public_pem,
        public_key_fingerprint=public_key_fingerprint(public_pem),
        active=True,
    )


def ensure_default_holders(register_keys: bool = False) -> list[HolderProfile]:
    holders: list[HolderProfile] = []
    for item in DEFAULT_HOLDERS:
        holder, _ = HolderProfile.objects.get_or_create(
            holder_id=item["holder_id"],
            defaults={"display_name": item["display_name"], "email": item["email"]},
        )
        _ensure_holder_key(holder)
        if register_keys:
            register_holder_key(holder)
        holders.append(holder)
    return holders


@require_GET
def wallet_ui(request: HttpRequest):
    ensure_default_holders()
    return render(request, "holder_app/wallet.html")


@require_GET
def list_credentials(request: HttpRequest) -> JsonResponse:
    ensure_default_holders()
    holder_id = request.GET.get("holder_id")
    records = WalletCredential.objects.select_related("holder").order_by("-created_at")
    if holder_id:
        records = records.filter(holder__holder_id=holder_id)
    return JsonResponse(
        {
            "credentials": [
                {
                    "wallet_id": record.id,
                    "holder_id": record.holder.holder_id if record.holder else "",
                    "holder_name": record.holder.display_name if record.holder else "Unassigned",
                    "credential_id": record.credential_id,
                    "issuer": record.issuer,
                    "created_at": record.created_at.isoformat(),
                    "credential": record.credential,
                }
                for record in records
            ]
        }
    )


@require_GET
def list_holders(request: HttpRequest) -> JsonResponse:
    holders = ensure_default_holders(register_keys=True)
    return JsonResponse(
        {
            "holders": [
                {
                    "holder_id": holder.holder_id,
                    "display_name": holder.display_name,
                    "email": holder.email,
                    "holder_url": holder_public_url(holder),
                    "key_id": holder.keypair.key_id,
                    "public_key_fingerprint": holder.keypair.public_key_fingerprint,
                }
                for holder in holders
            ]
        }
    )


@require_GET
def holder_public_key(request: HttpRequest, holder_id: str) -> JsonResponse:
    try:
        ensure_default_holders(register_keys=True)
        holder = HolderProfile.objects.get(holder_id=holder_id)
        return JsonResponse(
            {
                "holder": holder_public_url(holder),
                "holder_id": holder.holder_id,
                "key_id": holder.keypair.key_id,
                "key_type": "RSA",
                "algorithm": "PSS-MGF1-SHA256",
                "public_key_fingerprint": holder.keypair.public_key_fingerprint,
                "public_key_pem": holder.keypair.public_key_pem,
            }
        )
    except HolderProfile.DoesNotExist:
        return JsonResponse({"error": "Holder was not found."}, status=404)


@csrf_exempt
@require_POST
def receive_credential(request: HttpRequest) -> JsonResponse:
    try:
        credential = _json_body(request)
        validate_credential_structure(credential)
        holder_binding = credential.get("credentialSubject", {}).get("holder", {})
        holder_id = str(holder_binding.get("id", "")).strip()
        if not holder_id:
            raise ValueError("Credential must include credentialSubject.holder.id.")
        holder = HolderProfile.objects.get(holder_id=holder_id)
        record = WalletCredential.objects.create(
            holder=holder,
            credential=credential,
            issuer=str(credential["issuer"]),
            credential_id=str(credential["id"]),
        )
        return JsonResponse(
            {
                "received": True,
                "wallet_id": record.id,
                "holder_id": holder.holder_id,
                "credential_id": record.credential_id,
            },
            status=201,
        )
    except HolderProfile.DoesNotExist:
        return JsonResponse({"error": "Target holder was not found in the wallet."}, status=404)
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

        record = WalletCredential.objects.select_related("holder").get(id=wallet_id)
        if record.holder is None:
            raise ValueError("Credential is not assigned to a holder profile.")
        presentation = build_selective_presentation(record.credential, disclosed_keys, record.holder)
        return JsonResponse(presentation)
    except WalletCredential.DoesNotExist:
        return JsonResponse({"error": "Credential was not found in the wallet."}, status=404)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
