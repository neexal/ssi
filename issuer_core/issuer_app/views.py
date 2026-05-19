import json
import uuid
from datetime import datetime, timezone

from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .crypto import compile_hash_payload, get_or_create_active_keypair, salt_and_hash_claims, sign_payload
from .models import CredentialType


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
        name="IdentityProfile",
        defaults={
            "context_uri": "https://example.local/ssi/identity-profile/v1",
            "schema_version": "1.0",
            "allowed_fields": ["ID", "age", "status"],
        },
    )
    return credential_type


@require_GET
def dashboard(request: HttpRequest):
    keypair = get_or_create_active_keypair()
    return render(
        request,
        "issuer_app/dashboard.html",
        {
            "public_key_preview": keypair.public_key_pem.splitlines()[1][:48],
            "issuer_origin": ISSUER_ORIGIN,
        },
    )


@csrf_exempt
@require_POST
def issue_credential(request: HttpRequest) -> JsonResponse:
    try:
        body = _json_body(request)
        claims = body.get("claims", body)
        if not isinstance(claims, dict) or not claims:
            return JsonResponse({"error": "A non-empty claims object is required."}, status=400)

        credential_type = _default_credential_type()
        keypair = get_or_create_active_keypair()
        protected_claims = salt_and_hash_claims(claims)
        payload = compile_hash_payload(protected_claims)
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
                "claims": protected_claims,
            },
            "proof": {
                "type": "RsaSignaturePssSha256-2026",
                "created": now,
                "proofPurpose": "assertionMethod",
                "verificationMethod": f"{ISSUER_ORIGIN}/api/v1/pki/public-key/",
                "signature": signature,
            },
        }
        return JsonResponse(credential, status=201)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@require_GET
def public_key(request: HttpRequest) -> JsonResponse:
    keypair = get_or_create_active_keypair()
    return JsonResponse(
        {
            "issuer": ISSUER_ORIGIN,
            "key_type": "RSA",
            "algorithm": "PSS-MGF1-SHA256",
            "public_key_pem": keypair.public_key_pem,
        }
    )
