from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="WalletCredential",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("credential", models.JSONField()),
                ("issuer", models.URLField()),
                ("credential_id", models.CharField(db_index=True, max_length=256)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
