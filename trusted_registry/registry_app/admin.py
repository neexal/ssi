from django.contrib import admin

from .models import RevokedCredential, TrustedKey


@admin.register(TrustedKey)
class TrustedKeyAdmin(admin.ModelAdmin):
    list_display = ("entity_name", "entity_role", "entity_url", "key_id", "active", "updated_at")
    list_filter = ("entity_role", "active", "algorithm")
    search_fields = ("entity_name", "entity_url", "key_id", "public_key_fingerprint")


@admin.register(RevokedCredential)
class RevokedCredentialAdmin(admin.ModelAdmin):
    list_display = ("credential_id", "issuer_url", "revocation_reason", "revoked_at")
    list_filter = ("issuer_url", "revoked_at")
    search_fields = ("credential_id", "issuer_url", "revocation_reason", "revoked_by")
    readonly_fields = ("credential_id", "revoked_at")
