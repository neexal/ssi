from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registry_app", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RevokedCredential",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("credential_id", models.CharField(db_index=True, max_length=256, unique=True)),
                ("issuer_url", models.URLField()),
                ("revocation_reason", models.CharField(blank=True, max_length=256)),
                ("revoked_by", models.CharField(blank=True, max_length=160)),
                ("revoked_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("credential_id",),
                        name="unique_revoked_credential",
                    )
                ],
            },
        ),
    ]
