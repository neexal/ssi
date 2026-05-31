from urllib.parse import urlencode

import requests

from .crypto import public_key_fingerprint
from .models import IssuerKeyPair


REGISTRY_ORIGIN = "http://127.0.0.1:8004"
REGISTER_URL = f"{REGISTRY_ORIGIN}/api/v1/registry/keys/register/"
RESOLVE_URL = f"{REGISTRY_ORIGIN}/api/v1/registry/keys/resolve/"
REVOKE_URL = f"{REGISTRY_ORIGIN}/api/v1/registry/revocation/revoke/"
REQUEST_TIMEOUT_SECONDS = 3.0
ISSUER_KEY_ID = "default"


def register_issuer_key(keypair: IssuerKeyPair, issuer_origin: str) -> dict:
    payload = {
        "entity_name": "Issuer Server Core",
        "entity_url": issuer_origin,
        "entity_role": "issuer",
        "key_id": ISSUER_KEY_ID,
        "key_type": "RSA",
        "algorithm": "PSS-MGF1-SHA256",
        "public_key_pem": keypair.public_key_pem,
        "public_key_fingerprint": public_key_fingerprint(keypair.public_key_pem),
        "active": keypair.active,
    }
    response = requests.post(REGISTER_URL, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def resolve_holder_key(holder_url: str, key_id: str = "default") -> dict:
    query = urlencode({"entity_url": holder_url, "entity_role": "holder", "key_id": key_id})
    response = requests.get(f"{RESOLVE_URL}?{query}", timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()
    if payload.get("trusted") is not True:
        raise ValueError("Holder key is not trusted by the registry.")
    return payload


def revoke_credential(credential_id: str, issuer_origin: str, reason: str = "") -> dict:
    payload = {
        "credential_id": credential_id,
        "issuer_url": issuer_origin,
        "revocation_reason": reason,
        "revoked_by": "Issuer Admin",
    }
    response = requests.post(REVOKE_URL, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()
