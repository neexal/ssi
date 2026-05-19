from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4


REQUIRED_VC_KEYS = {"@context", "id", "type", "issuer", "credentialSubject", "proof"}
REQUIRED_CLAIM_KEYS = {"value", "salt", "hash"}


def validate_credential_structure(credential: dict) -> None:
    missing = REQUIRED_VC_KEYS.difference(credential.keys())
    if missing:
        raise ValueError(f"Credential is missing required keys: {', '.join(sorted(missing))}.")

    claims = credential.get("credentialSubject", {}).get("claims")
    if not isinstance(claims, dict) or not claims:
        raise ValueError("Credential must contain a non-empty credentialSubject.claims object.")

    for claim_name, claim_block in claims.items():
        if not isinstance(claim_block, dict):
            raise ValueError(f"Claim '{claim_name}' must be an object.")
        missing_claim_keys = REQUIRED_CLAIM_KEYS.difference(claim_block.keys())
        if missing_claim_keys:
            raise ValueError(
                f"Claim '{claim_name}' is missing keys: {', '.join(sorted(missing_claim_keys))}."
            )


def build_selective_presentation(credential: dict, disclosed_keys: list[str]) -> dict:
    validate_credential_structure(credential)
    disclosed = {str(key) for key in disclosed_keys}
    reduced_credential = deepcopy(credential)
    claims = reduced_credential["credentialSubject"]["claims"]

    for claim_name, claim_block in claims.items():
        if claim_name not in disclosed:
            claim_block.pop("value", None)
            claim_block.pop("salt", None)

    return {
        "@context": ["https://example.local/ssi/presentation/v1"],
        "id": f"urn:uuid:{uuid4()}",
        "type": ["VerifiablePresentation", "SelectiveDisclosurePresentation"],
        "holder": "http://127.0.0.1:8002",
        "created": datetime.now(timezone.utc).isoformat(),
        "verifiableCredential": reduced_credential,
    }
