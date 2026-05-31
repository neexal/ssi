import json
from urllib.parse import urlparse

from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .crypto import public_key_fingerprint
from .models import RevokedCredential, TrustedKey


TRUSTED_LOCAL_HOSTS = {"127.0.0.1", "localhost"}


def _json_body(request: HttpRequest) -> dict:
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON.") from exc
    if not isinstance(body, dict):
        raise ValueError("Request JSON must be an object.")
    return body


def _validate_entity_url(entity_url: str) -> None:
    parsed = urlparse(entity_url)
    if parsed.scheme != "http" or parsed.hostname not in TRUSTED_LOCAL_HOSTS or not parsed.port:
        raise ValueError("Only local HTTP service URLs are accepted by this demo registry.")


def _key_payload(key: TrustedKey) -> dict:
    return {
        "id": key.id,
        "entity_name": key.entity_name,
        "entity_url": key.entity_url,
        "entity_role": key.entity_role,
        "key_id": key.key_id,
        "key_type": key.key_type,
        "algorithm": key.algorithm,
        "public_key_pem": key.public_key_pem,
        "public_key_fingerprint": key.public_key_fingerprint,
        "active": key.active,
        "created_at": key.created_at.isoformat(),
        "updated_at": key.updated_at.isoformat(),
    }


def _revocation_payload(revoked: RevokedCredential) -> dict:
    return {
        "credential_id": revoked.credential_id,
        "issuer_url": revoked.issuer_url,
        "revocation_reason": revoked.revocation_reason,
        "revoked_by": revoked.revoked_by,
        "revoked_at": revoked.revoked_at.isoformat(),
    }


@require_GET
def registry_ui(request: HttpRequest):
    return render(request, "registry_app/registry.html")


@require_GET
def list_keys(request: HttpRequest) -> JsonResponse:
    records = TrustedKey.objects.order_by("entity_role", "entity_url", "key_id")
    return JsonResponse({"keys": [_key_payload(record) for record in records]})


@csrf_exempt
@require_POST
def register_key(request: HttpRequest) -> JsonResponse:
    try:
        body = _json_body(request)
        entity_name = str(body.get("entity_name", "")).strip() or "Unnamed Entity"
        entity_url = str(body.get("entity_url", "")).strip()
        entity_role = str(body.get("entity_role", "")).strip().lower()
        key_id = str(body.get("key_id", "default")).strip() or "default"
        key_type = str(body.get("key_type", "RSA")).strip()
        algorithm = str(body.get("algorithm", "PSS-MGF1-SHA256")).strip()
        public_key_pem = str(body.get("public_key_pem", "")).strip()
        active = bool(body.get("active", True))

        if entity_role not in {"issuer", "holder", "verifier"}:
            raise ValueError("entity_role must be issuer, holder, or verifier.")
        _validate_entity_url(entity_url)
        if "BEGIN PUBLIC KEY" not in public_key_pem:
            raise ValueError("public_key_pem must contain a PEM encoded public key.")

        record, created = TrustedKey.objects.update_or_create(
            entity_url=entity_url,
            entity_role=entity_role,
            key_id=key_id,
            defaults={
                "entity_name": entity_name,
                "key_type": key_type,
                "algorithm": algorithm,
                "public_key_pem": public_key_pem,
                "public_key_fingerprint": public_key_fingerprint(public_key_pem),
                "active": active,
            },
        )
        return JsonResponse({"registered": True, "created": created, "key": _key_payload(record)}, status=201)
    except ValueError as exc:
        return JsonResponse({"registered": False, "error": str(exc)}, status=400)


@require_GET
def resolve_key(request: HttpRequest) -> JsonResponse:
    entity_url = str(request.GET.get("entity_url", "")).strip()
    entity_role = str(request.GET.get("entity_role", "")).strip().lower()
    key_id = str(request.GET.get("key_id", "default")).strip() or "default"

    if not entity_url or not entity_role:
        return JsonResponse({"trusted": False, "error": "entity_url and entity_role are required."}, status=400)

    record = (
        TrustedKey.objects.filter(
            entity_url=entity_url,
            entity_role=entity_role,
            key_id=key_id,
            active=True,
        )
        .order_by("-updated_at")
        .first()
    )
    if not record:
        return JsonResponse({"trusted": False, "error": "No active trusted key is registered."}, status=404)

    payload = _key_payload(record)
    payload["trusted"] = True
    return JsonResponse(payload)


@csrf_exempt
@require_POST
def revoke_credential(request: HttpRequest) -> JsonResponse:
    try:
        body = _json_body(request)
        credential_id = str(body.get("credential_id", "")).strip()
        issuer_url = str(body.get("issuer_url", "")).strip()
        reason = str(body.get("revocation_reason", "")).strip()
        revoked_by = str(body.get("revoked_by", "")).strip() or "Unknown"

        if not credential_id:
            raise ValueError("credential_id is required.")
        if not issuer_url:
            raise ValueError("issuer_url is required.")

        _validate_entity_url(issuer_url)

        record, created = RevokedCredential.objects.update_or_create(
            credential_id=credential_id,
            defaults={
                "issuer_url": issuer_url,
                "revocation_reason": reason,
                "revoked_by": revoked_by,
            },
        )

        return JsonResponse(_revocation_payload(record), status=201)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@require_GET
def check_revocation(request: HttpRequest) -> JsonResponse:
    credential_id = str(request.GET.get("credential_id", "")).strip()

    if not credential_id:
        return JsonResponse({"error": "credential_id is required."}, status=400)

    record = RevokedCredential.objects.filter(credential_id=credential_id).first()

    if not record:
        return JsonResponse(
            {
                "revoked": False,
                "credential_id": credential_id,
            }
        )

    return JsonResponse(
        {
            "revoked": True,
            **_revocation_payload(record),
        }
    )


@require_GET
def list_revoked(request: HttpRequest) -> JsonResponse:
    issuer_url = str(request.GET.get("issuer_url", "")).strip()

    records = RevokedCredential.objects.order_by("-revoked_at")
    if issuer_url:
        records = records.filter(issuer_url=issuer_url)

    return JsonResponse({"revoked": [_revocation_payload(record) for record in records]})
