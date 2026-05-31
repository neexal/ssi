import json
import uuid
from datetime import datetime, timezone

from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .crypto import (
    compile_hash_payload,
    get_or_create_active_keypair,
    public_key_fingerprint,
    salt_and_hash_claims,
    sign_payload,
)
from .models import CredentialType
from .registry import ISSUER_KEY_ID, REGISTRY_ORIGIN, register_issuer_key, resolve_holder_key, revoke_credential


ISSUER_ORIGIN = "http://127.0.0.1:8001"


def _json_body(request: HttpRequest) -> dict:
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON.") from exc
    if not isinstance(body, dict):
        raise ValueError("Request JSON must be an object.")
    return body


def _default_credential_type() -> CredentialType:
    credential_type, _ = CredentialType.objects.get_or_create(
        name="UniversityDegreeCredential",
        defaults={
            "context_uri": "https://example.local/ssi/university-degree/v1",
            "schema_version": "1.0",
            "allowed_fields": [
                "student_name",
                "student_id",
                "degree_title",
                "university_name",
                "graduation_year",
                "department",
                "grade_summary",
            ],
        },
    )
    return credential_type


@require_GET
def dashboard(request: HttpRequest):
    keypair = get_or_create_active_keypair()
    registry_status = "not checked"
    try:
        register_issuer_key(keypair, ISSUER_ORIGIN)
        registry_status = "registered"
    except Exception:
        registry_status = "registry unavailable"
    return render(
        request,
        "issuer_app/dashboard.html",
        {
            "public_key_preview": keypair.public_key_pem.splitlines()[1][:48],
            "issuer_origin": ISSUER_ORIGIN,
            "registry_origin": REGISTRY_ORIGIN,
            "registry_status": registry_status,
        },
    )


@csrf_exempt
@require_POST
def issue_credential(request: HttpRequest) -> JsonResponse:
    try:
        body = _json_body(request)
        claims = body.get("claims", body)
        holder = body.get("holder")
        if not isinstance(claims, dict) or not claims:
            return JsonResponse({"error": "A non-empty claims object is required."}, status=400)
        if not isinstance(holder, dict):
            return JsonResponse({"error": "A holder object is required."}, status=400)

        credential_type = _default_credential_type()
        keypair = get_or_create_active_keypair()
        register_issuer_key(keypair, ISSUER_ORIGIN)
        holder_id = str(holder.get("id", "")).strip()
        holder_url = str(holder.get("url", "")).strip()
        holder_key_id = str(holder.get("key_id", "default")).strip() or "default"
        if not holder_id or not holder_url:
            return JsonResponse({"error": "holder.id and holder.url are required."}, status=400)
        holder_key = resolve_holder_key(holder_url, holder_key_id)
        holder_fingerprint = str(holder_key["public_key_fingerprint"])
        protected_claims = salt_and_hash_claims(claims)
        holder_binding_payload = f"{holder_url}|{holder_key_id}|{holder_fingerprint}"
        payload = compile_hash_payload(protected_claims, holder_binding_payload)
        signature = sign_payload(payload, keypair.private_key_pem)
        now = datetime.now(timezone.utc).isoformat()

        credential = {
            "@context": [credential_type.context_uri],
            "id": f"urn:uuid:{uuid.uuid4()}",
            "type": ["VerifiableCredential", credential_type.name],
            "issuer": ISSUER_ORIGIN,
            "issuanceDate": now,
            "credentialSchema": {
                "id": credential_type.context_uri,
                "type": credential_type.name,
                "version": credential_type.schema_version,
            },
            "credentialSubject": {
                "id": f"urn:subject:{uuid.uuid4()}",
                "holder": {
                    "id": holder_id,
                    "url": holder_url,
                    "keyId": holder_key_id,
                    "publicKeyFingerprint": holder_fingerprint,
                },
                "claims": protected_claims,
            },
            "proof": {
                "type": "RsaSignaturePssSha256-2026",
                "created": now,
                "proofPurpose": "assertionMethod",
                "verificationMethod": f"{REGISTRY_ORIGIN}/api/v1/registry/keys/resolve/?entity_url={ISSUER_ORIGIN}&entity_role=issuer&key_id={ISSUER_KEY_ID}",
                "keyId": ISSUER_KEY_ID,
                "publicKeyFingerprint": public_key_fingerprint(keypair.public_key_pem),
                "signature": signature,
            },
        }
        return JsonResponse(credential, status=201)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({"error": f"Trusted key resolution failed: {exc.__class__.__name__}."}, status=503)


@require_GET
def public_key(request: HttpRequest) -> JsonResponse:
    keypair = get_or_create_active_keypair()
    return JsonResponse(
        {
            "issuer": ISSUER_ORIGIN,
            "key_type": "RSA",
            "algorithm": "PSS-MGF1-SHA256",
            "key_id": ISSUER_KEY_ID,
            "public_key_fingerprint": public_key_fingerprint(keypair.public_key_pem),
            "public_key_pem": keypair.public_key_pem,
        }
    )


@csrf_exempt
@require_POST
def revoke_issued_credential(request: HttpRequest) -> JsonResponse:
    try:
        body = _json_body(request)
        credential_id = str(body.get("credential_id", "")).strip()
        reason = str(body.get("reason", "")).strip()

        if not credential_id:
            return JsonResponse({"error": "credential_id is required."}, status=400)

        result = revoke_credential(credential_id, ISSUER_ORIGIN, reason)
        return JsonResponse(result, status=201)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({"error": f"Revocation failed: {exc.__class__.__name__}."}, status=503)
