from django.db import models


class CredentialType(models.Model):
    name = models.CharField(max_length=128, unique=True)
    context_uri = models.URLField(default="https://example.local/ssi/context/v1")
    schema_version = models.CharField(max_length=32, default="1.0")
    allowed_fields = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.name} v{self.schema_version}"


class IssuerKeyPair(models.Model):
    label = models.CharField(max_length=128, unique=True, default="default-issuer-key")
    private_key_pem = models.TextField()
    public_key_pem = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.label
