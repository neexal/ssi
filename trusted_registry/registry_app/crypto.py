import hashlib


def public_key_fingerprint(public_key_pem: str) -> str:
    return hashlib.sha256(public_key_pem.strip().encode("utf-8")).hexdigest()
