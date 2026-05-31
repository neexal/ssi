from django.contrib import admin

from .models import HolderKeyPair, HolderProfile, WalletCredential


@admin.register(HolderProfile)
class HolderProfileAdmin(admin.ModelAdmin):
    list_display = ("holder_id", "display_name", "email", "created_at")
    search_fields = ("holder_id", "display_name", "email")


@admin.register(HolderKeyPair)
class HolderKeyPairAdmin(admin.ModelAdmin):
    list_display = ("holder", "key_id", "active", "created_at")
    search_fields = ("holder__holder_id", "public_key_fingerprint")


@admin.register(WalletCredential)
class WalletCredentialAdmin(admin.ModelAdmin):
    list_display = ("credential_id", "holder", "issuer", "created_at")
    search_fields = ("credential_id", "issuer", "holder__holder_id")
