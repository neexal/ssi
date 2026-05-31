import hashlib
import secrets
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .models import IssuerKeyPair


HASH_JOINER = "\x00"
RSA_KEY_SIZE = 2048
RSA_PUBLIC_EXPONENT = 65537


@dataclass(frozen=True)
class HashedClaim:
    value: str
    salt: str
    hash: str


def generate_rsa_keypair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(
        public_exponent=RSA_PUBLIC_EXPONENT,
        key_size=RSA_KEY_SIZE,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return private_pem, public_pem


def get_or_create_active_keypair() -> IssuerKeyPair:
    keypair = IssuerKeyPair.objects.filter(active=True).order_by("-created_at").first()
    if keypair:
        return keypair
    private_pem, public_pem = generate_rsa_keypair()
    return IssuerKeyPair.objects.create(
        label="default-issuer-key",
        private_key_pem=private_pem,
        public_key_pem=public_pem,
        active=True,
    )


def compute_claim_hash(value: str, salt: str) -> str:
    return hashlib.sha256(f"{value}{salt}".encode("utf-8")).hexdigest()


def salt_and_hash_claims(raw_claims: dict[str, object]) -> dict[str, dict[str, str]]:
    protected_claims: dict[str, dict[str, str]] = {}
    for key, value in raw_claims.items():
        normalized_value = str(value)
        salt = secrets.token_hex(16)
        protected_claims[str(key)] = HashedClaim(
            value=normalized_value,
            salt=salt,
            hash=compute_claim_hash(normalized_value, salt),
        ).__dict__
    return protected_claims


def public_key_fingerprint(public_key_pem: str) -> str:
    return hashlib.sha256(public_key_pem.strip().encode("utf-8")).hexdigest()


def compile_hash_payload(claim_blocks: dict[str, dict[str, str]], holder_binding: str | None = None) -> bytes:
    hashes_to_sign = sorted(str(block["hash"]) for block in claim_blocks.values())
    if holder_binding:
        hashes_to_sign.append(f"holder:{holder_binding}")
        hashes_to_sign = sorted(hashes_to_sign)
    return HASH_JOINER.join(hashes_to_sign).encode("utf-8")


def sign_payload(payload: bytes, private_key_pem: str) -> str:
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
    )
    signature = private_key.sign(
        payload,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return signature.hex()
