import hashlib
import json
from urllib.parse import urlencode, urlparse

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


HASH_JOINER = "\x00"
REGISTRY_ORIGIN = "http://127.0.0.1:8004"
REGISTRY_RESOLVE_PATH = "/api/v1/registry/keys/resolve/"
REGISTRY_REVOCATION_PATH = "/api/v1/registry/revocation/check/"
REQUEST_TIMEOUT_SECONDS = 3.0


class VerificationError(Exception):
    pass


def compute_claim_hash(value: str, salt: str) -> str:
    return hashlib.sha256(f"{value}{salt}".encode("utf-8")).hexdigest()


def public_key_fingerprint(public_key_pem: str) -> str:
    return hashlib.sha256(public_key_pem.strip().encode("utf-8")).hexdigest()


def compile_hash_payload(claim_hashes: list[str], holder_binding: str | None = None) -> bytes:
    if not all(isinstance(item, str) and item for item in claim_hashes):
        raise VerificationError("Every evaluated claim hash must be a non-empty string.")
    payload_items = list(claim_hashes)
    if holder_binding:
        payload_items.append(f"holder:{holder_binding}")
    return HASH_JOINER.join(sorted(payload_items)).encode("utf-8")


def canonical_presentation_payload(presentation: dict) -> bytes:
    unsigned = {key: value for key, value in presentation.items() if key != "holderProof"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")


def trusted_key_url(entity_url: str, entity_role: str, key_id: str) -> str:
    parsed = urlparse(entity_url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not parsed.port:
        raise VerificationError("Entity route is outside the trusted local boundary.")
    query = urlencode({"entity_url": entity_url, "entity_role": entity_role, "key_id": key_id})
    return f"{REGISTRY_ORIGIN}{REGISTRY_RESOLVE_PATH}?{query}"


def check_credential_revocation(credential_id: str) -> None:
    query = urlencode({"credential_id": credential_id})
    response = requests.get(
        f"{REGISTRY_ORIGIN}{REGISTRY_REVOCATION_PATH}?{query}",
        timeout=REQUEST_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    payload = response.json()
    
    if payload.get("revoked") is True:
        reason = payload.get("revocation_reason", "No reason provided")
        raise VerificationError(f"Credential has been revoked: {reason}")


def fetch_trusted_public_key(entity_url: str, entity_role: str, key_id: str, expected_fingerprint: str | None) -> str:
    response = requests.get(trusted_key_url(entity_url, entity_role, key_id), timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()
    if payload.get("trusted") is not True:
        raise VerificationError("Trusted registry did not confirm this key.")
    public_key_pem = payload.get("public_key_pem")
    if not isinstance(public_key_pem, str) or "BEGIN PUBLIC KEY" not in public_key_pem:
        raise VerificationError("Trusted registry returned an invalid public key payload.")
    computed_fingerprint = public_key_fingerprint(public_key_pem)
    if payload.get("public_key_fingerprint") != computed_fingerprint:
        raise VerificationError("Trusted registry key fingerprint does not match the public key.")
    if expected_fingerprint and expected_fingerprint != computed_fingerprint:
        raise VerificationError("Expected key fingerprint does not match the trusted public key.")
    return public_key_pem


def evaluate_claims(claims: dict) -> tuple[list[str], dict[str, str]]:
    evaluated_hashes: list[str] = []
    disclosed_claims: dict[str, str] = {}

    if not isinstance(claims, dict) or not claims:
        raise VerificationError("Presentation contains no credential claims.")

    for claim_name, claim_block in claims.items():
        if not isinstance(claim_block, dict):
            raise VerificationError(f"Claim '{claim_name}' must be an object.")

        has_value = "value" in claim_block
        has_salt = "salt" in claim_block
        claim_hash = claim_block.get("hash")
        if not isinstance(claim_hash, str) or not claim_hash:
            raise VerificationError(f"Claim '{claim_name}' is missing a valid hash.")

        if has_value or has_salt:
            if not (has_value and has_salt):
                raise VerificationError(f"Claim '{claim_name}' has partial disclosure metadata.")
            value = claim_block["value"]
            salt = claim_block["salt"]
            if not isinstance(value, str) or not isinstance(salt, str):
                raise VerificationError(f"Claim '{claim_name}' value and salt must be strings.")
            recomputed_hash = compute_claim_hash(value, salt)
            if recomputed_hash != claim_hash:
                raise VerificationError(f"Claim '{claim_name}' hash does not match its disclosed value and salt.")
            evaluated_hashes.append(recomputed_hash)
            disclosed_claims[str(claim_name)] = value
        else:
            evaluated_hashes.append(claim_hash)

    return evaluated_hashes, disclosed_claims


def verify_signature(public_key_pem: str, payload: bytes, signature_hex: str) -> None:
    if not isinstance(signature_hex, str) or not signature_hex:
        raise VerificationError("Proof is missing a hex signature.")
    try:
        signature = bytes.fromhex(signature_hex)
    except ValueError as exc:
        raise VerificationError("Proof signature is not valid hex.") from exc

    public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    public_key.verify(
        signature,
        payload,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )


def verify_presentation_document(presentation: dict) -> dict:
    if not isinstance(presentation, dict):
        raise VerificationError("Presentation must be a JSON object.")

    credential = presentation.get("verifiableCredential")
    if not isinstance(credential, dict):
        raise VerificationError("Presentation must include a verifiableCredential object.")

    credential_id = credential.get("id")
    if isinstance(credential_id, str) and credential_id:
        check_credential_revocation(credential_id)

    issuer = credential.get("issuer")
    if not isinstance(issuer, str):
        raise VerificationError("Credential issuer must be a route string.")

    subject = credential.get("credentialSubject", {})
    holder_binding = subject.get("holder")
    if not isinstance(holder_binding, dict):
        raise VerificationError("Credential is not bound to a holder key.")
    holder_url = holder_binding.get("url")
    holder_key_id = str(holder_binding.get("keyId", "default"))
    holder_fingerprint = holder_binding.get("publicKeyFingerprint")
    if not isinstance(holder_url, str) or not isinstance(holder_fingerprint, str):
        raise VerificationError("Credential holder binding is incomplete.")

    evaluated_hashes, disclosed_claims = evaluate_claims(subject.get("claims"))
    holder_binding_payload = f"{holder_url}|{holder_key_id}|{holder_fingerprint}"
    issuer_payload = compile_hash_payload(evaluated_hashes, holder_binding_payload)

    issuer_proof = credential.get("proof")
    if not isinstance(issuer_proof, dict):
        raise VerificationError("Credential proof must be an object.")
    issuer_key_id = str(issuer_proof.get("keyId", "default"))
    issuer_fingerprint = issuer_proof.get("publicKeyFingerprint")
    if issuer_fingerprint is not None and not isinstance(issuer_fingerprint, str):
        raise VerificationError("Issuer proof fingerprint must be a string.")
    issuer_public_key_pem = fetch_trusted_public_key(issuer, "issuer", issuer_key_id, issuer_fingerprint)
    verify_signature(issuer_public_key_pem, issuer_payload, issuer_proof.get("signature"))

    holder_proof = presentation.get("holderProof")
    if not isinstance(holder_proof, dict):
        raise VerificationError("Presentation is missing holder proof.")
    if holder_proof.get("holder") != holder_url:
        raise VerificationError("Holder proof does not match credential holder binding.")
    holder_proof_key_id = str(holder_proof.get("keyId", holder_key_id))
    if holder_proof_key_id != holder_key_id:
        raise VerificationError("Holder proof key id does not match credential holder binding.")
    if holder_proof.get("publicKeyFingerprint") != holder_fingerprint:
        raise VerificationError("Holder proof fingerprint does not match credential holder binding.")
    holder_public_key_pem = fetch_trusted_public_key(holder_url, "holder", holder_key_id, holder_fingerprint)
    verify_signature(holder_public_key_pem, canonical_presentation_payload(presentation), holder_proof.get("signature"))

    return {"valid": True, "holder": holder_url, "disclosed_claims": disclosed_claims}


def safe_verify(presentation: dict) -> dict:
    try:
        return verify_presentation_document(presentation)
    except InvalidSignature:
        return {"valid": False, "reason": "RSA-PSS signature verification failed."}
    except requests.RequestException as exc:
        return {"valid": False, "reason": f"Unable to resolve trusted public key: {exc.__class__.__name__}."}
    except (VerificationError, TypeError, ValueError) as exc:
        return {"valid": False, "reason": str(exc)}
    except Exception:
        return {"valid": False, "reason": "Unexpected verifier failure while processing presentation."}
