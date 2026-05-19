import hashlib
from urllib.parse import urlparse

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


HASH_JOINER = "\x00"
ISSUER_PUBLIC_KEY_PATH = "/api/v1/pki/public-key/"
REQUEST_TIMEOUT_SECONDS = 3.0


class VerificationError(Exception):
    pass


def compute_claim_hash(value: str, salt: str) -> str:
    return hashlib.sha256(f"{value}{salt}".encode("utf-8")).hexdigest()


def compile_hash_payload(claim_hashes: list[str]) -> bytes:
    if not all(isinstance(item, str) and item for item in claim_hashes):
        raise VerificationError("Every evaluated claim hash must be a non-empty string.")
    return HASH_JOINER.join(sorted(claim_hashes)).encode("utf-8")


def issuer_public_key_url(issuer: str) -> str:
    parsed = urlparse(issuer)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.port != 8001:
        raise VerificationError("Issuer route is outside the trusted local issuer boundary.")
    return f"{parsed.scheme}://{parsed.netloc}{ISSUER_PUBLIC_KEY_PATH}"


def fetch_issuer_public_key(issuer: str) -> str:
    url = issuer_public_key_url(issuer)
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()
    public_key_pem = payload.get("public_key_pem")
    if not isinstance(public_key_pem, str) or "BEGIN PUBLIC KEY" not in public_key_pem:
        raise VerificationError("Issuer returned an invalid public key payload.")
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
        raise VerificationError("Credential proof is missing a hex signature.")
    try:
        signature = bytes.fromhex(signature_hex)
    except ValueError as exc:
        raise VerificationError("Credential proof signature is not valid hex.") from exc

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

    issuer = credential.get("issuer")
    if not isinstance(issuer, str):
        raise VerificationError("Credential issuer must be a route string.")

    claims = credential.get("credentialSubject", {}).get("claims")
    evaluated_hashes, disclosed_claims = evaluate_claims(claims)
    payload = compile_hash_payload(evaluated_hashes)

    proof = credential.get("proof")
    if not isinstance(proof, dict):
        raise VerificationError("Credential proof must be an object.")

    public_key_pem = fetch_issuer_public_key(issuer)
    verify_signature(public_key_pem, payload, proof.get("signature"))
    return {"valid": True, "disclosed_claims": disclosed_claims}


def safe_verify(presentation: dict) -> dict:
    try:
        return verify_presentation_document(presentation)
    except InvalidSignature:
        return {"valid": False, "reason": "RSA-PSS signature verification failed."}
    except requests.RequestException as exc:
        return {"valid": False, "reason": f"Unable to fetch issuer public key: {exc.__class__.__name__}."}
    except (VerificationError, TypeError, ValueError) as exc:
        return {"valid": False, "reason": str(exc)}
    except Exception:
        return {"valid": False, "reason": "Unexpected verifier failure while processing presentation."}
