from django.db import models


class HolderProfile(models.Model):
    holder_id = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.display_name


class HolderKeyPair(models.Model):
    holder = models.OneToOneField(HolderProfile, related_name="keypair", on_delete=models.CASCADE)
    key_id = models.CharField(max_length=100, default="default")
    private_key_pem = models.TextField()
    public_key_pem = models.TextField()
    public_key_fingerprint = models.CharField(max_length=64, db_index=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.holder.holder_id}:{self.key_id}"


class WalletCredential(models.Model):
    holder = models.ForeignKey(HolderProfile, null=True, blank=True, on_delete=models.CASCADE)
    credential = models.JSONField()
    issuer = models.URLField()
    credential_id = models.CharField(max_length=256, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.credential_id
