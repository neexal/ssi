from django.contrib import admin
from django.urls import path

from registry_app import views

urlpatterns = [
    path("", views.registry_ui, name="registry-ui"),
    path("admin/", admin.site.urls),
    path("api/v1/registry/keys/", views.list_keys, name="registry-keys"),
    path("api/v1/registry/keys/register/", views.register_key, name="registry-register-key"),
    path("api/v1/registry/keys/resolve/", views.resolve_key, name="registry-resolve-key"),
    path("api/v1/registry/revocation/revoke/", views.revoke_credential, name="registry-revoke-credential"),
    path("api/v1/registry/revocation/check/", views.check_revocation, name="registry-check-revocation"),
    path("api/v1/registry/revocation/list/", views.list_revoked, name="registry-list-revoked"),
]
