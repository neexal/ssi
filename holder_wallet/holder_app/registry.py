import requests

from .crypto import public_key_fingerprint
from .models import HolderProfile


HOLDER_ORIGIN = "http://127.0.0.1:8002"
REGISTRY_ORIGIN = "http://127.0.0.1:8004"
REGISTER_URL = f"{REGISTRY_ORIGIN}/api/v1/registry/keys/register/"
REQUEST_TIMEOUT_SECONDS = 3.0


def holder_public_url(holder: HolderProfile) -> str:
    return f"{HOLDER_ORIGIN}/wallet/holders/{holder.holder_id}"


def register_holder_key(holder: HolderProfile) -> dict:
    keypair = holder.keypair
    payload = {
        "entity_name": holder.display_name,
        "entity_url": holder_public_url(holder),
        "entity_role": "holder",
        "key_id": keypair.key_id,
        "key_type": "RSA",
        "algorithm": "PSS-MGF1-SHA256",
        "public_key_pem": keypair.public_key_pem,
        "public_key_fingerprint": public_key_fingerprint(keypair.public_key_pem),
        "active": keypair.active,
    }
    response = requests.post(REGISTER_URL, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()
