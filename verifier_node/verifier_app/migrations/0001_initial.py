from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="VerificationAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("presentation_id", models.CharField(blank=True, max_length=256)),
                ("credential_id", models.CharField(blank=True, max_length=256)),
                ("issuer", models.URLField(blank=True)),
                ("valid", models.BooleanField(default=False)),
                ("reason", models.TextField(blank=True)),
                ("disclosed_claims", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
