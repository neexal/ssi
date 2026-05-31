from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="TrustedKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("entity_name", models.CharField(max_length=160)),
                ("entity_url", models.URLField()),
                (
                    "entity_role",
                    models.CharField(
                        choices=[("issuer", "Issuer"), ("holder", "Holder"), ("verifier", "Verifier")],
                        max_length=32,
                    ),
                ),
                ("key_id", models.CharField(default="default", max_length=160)),
                ("key_type", models.CharField(default="RSA", max_length=32)),
                ("algorithm", models.CharField(default="PSS-MGF1-SHA256", max_length=80)),
                ("public_key_pem", models.TextField()),
                ("public_key_fingerprint", models.CharField(db_index=True, max_length=64)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("entity_url", "entity_role", "key_id"),
                        name="unique_trusted_key_per_entity_role_key",
                    )
                ],
            },
        ),
    ]
