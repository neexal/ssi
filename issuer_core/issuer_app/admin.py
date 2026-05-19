from django.contrib import admin

from .models import CredentialType, IssuerKeyPair


@admin.register(CredentialType)
class CredentialTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "schema_version", "created_at")
    search_fields = ("name",)


@admin.register(IssuerKeyPair)
class IssuerKeyPairAdmin(admin.ModelAdmin):
    list_display = ("label", "active", "created_at")
    readonly_fields = ("created_at",)
