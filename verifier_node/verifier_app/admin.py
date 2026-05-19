from django.contrib import admin

from .models import VerificationAudit


@admin.register(VerificationAudit)
class VerificationAuditAdmin(admin.ModelAdmin):
    list_display = ("presentation_id", "credential_id", "issuer", "valid", "created_at")
    list_filter = ("valid", "created_at")
    search_fields = ("presentation_id", "credential_id", "issuer")
