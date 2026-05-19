from django.contrib import admin

from .models import WalletCredential


@admin.register(WalletCredential)
class WalletCredentialAdmin(admin.ModelAdmin):
    list_display = ("credential_id", "issuer", "created_at")
    search_fields = ("credential_id", "issuer")
