from django.contrib import admin
from django.urls import path

from holder_app import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("wallet/ui/", views.wallet_ui, name="wallet-ui"),
    path("api/v1/wallet/holders/", views.list_holders, name="wallet-holders"),
    path("api/v1/wallet/holders/<str:holder_id>/public-key/", views.holder_public_key, name="holder-public-key"),
    path("api/v1/wallet/holders/create/", views.create_holder, name="holder-create"),
    path("api/v1/wallet/credentials/", views.list_credentials, name="wallet-credentials"),
    path("api/v1/wallet/receive/", views.receive_credential, name="receive-credential"),
    path("api/v1/wallet/presentation/generate/", views.generate_presentation, name="generate-presentation"),
]
