from django.contrib import admin
from django.urls import path

from verifier_app import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/verify/", views.verify_presentation, name="verify-presentation"),
    path("api/v1/verify/audits/", views.audit_events, name="verify-audits"),
]
