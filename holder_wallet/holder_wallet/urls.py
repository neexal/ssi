from django.contrib import admin
from django.urls import path

from holder_app import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("wallet/ui/", views.wallet_ui, name="wallet-ui"),
    path("api/v1/wallet/credentials/", views.list_credentials, name="wallet-credentials"),
    path("api/v1/wallet/receive/", views.receive_credential, name="receive-credential"),
    path("api/v1/wallet/presentation/generate/", views.generate_presentation, name="generate-presentation"),
]
