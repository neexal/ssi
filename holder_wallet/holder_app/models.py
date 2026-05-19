from django.db import models


class WalletCredential(models.Model):
    credential = models.JSONField()
    issuer = models.URLField()
    credential_id = models.CharField(max_length=256, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.credential_id
