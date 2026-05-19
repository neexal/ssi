from django.db import models


class VerificationAudit(models.Model):
    presentation_id = models.CharField(max_length=256, blank=True)
    credential_id = models.CharField(max_length=256, blank=True)
    issuer = models.URLField(blank=True)
    valid = models.BooleanField(default=False)
    reason = models.TextField(blank=True)
    disclosed_claims = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        state = "valid" if self.valid else "invalid"
        return f"{state} {self.presentation_id or self.credential_id}"
