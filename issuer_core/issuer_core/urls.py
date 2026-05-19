from django.contrib import admin
from django.urls import path

from issuer_app import views

urlpatterns = [
    path("admin/dashboard/", views.dashboard, name="issuer-dashboard"),
    path("admin/", admin.site.urls),
    path("api/v1/issue/", views.issue_credential, name="issue-credential"),
    path("api/v1/pki/public-key/", views.public_key, name="issuer-public-key"),
]
