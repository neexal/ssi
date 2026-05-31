from django.db import models


class TrustedKey(models.Model):
    ROLE_CHOICES = [
        ("issuer", "Issuer"),
        ("holder", "Holder"),
        ("verifier", "Verifier"),
    ]

    entity_name = models.CharField(max_length=160)
    entity_url = models.URLField()
    entity_role = models.CharField(max_length=32, choices=ROLE_CHOICES)
    key_id = models.CharField(max_length=160, default="default")
    key_type = models.CharField(max_length=32, default="RSA")
    algorithm = models.CharField(max_length=80, default="PSS-MGF1-SHA256")
    public_key_pem = models.TextField()
    public_key_fingerprint = models.CharField(max_length=64, db_index=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["entity_url", "entity_role", "key_id"],
                name="unique_trusted_key_per_entity_role_key",
            )
        ]

    def __str__(self) -> str:
        return f"{self.entity_role}:{self.entity_url}:{self.key_id}"


class RevokedCredential(models.Model):
    credential_id = models.CharField(max_length=256, unique=True, db_index=True)
    issuer_url = models.URLField()
    revocation_reason = models.CharField(max_length=256, blank=True)
    revoked_by = models.CharField(max_length=160, blank=True)
    revoked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["credential_id"],
                name="unique_revoked_credential",
            )
        ]

    def __str__(self) -> str:
        return f"Revoked: {self.credential_id}"
