from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("holder_app", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="HolderProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("holder_id", models.CharField(max_length=100, unique=True)),
                ("display_name", models.CharField(max_length=200)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="HolderKeyPair",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key_id", models.CharField(default="default", max_length=100)),
                ("private_key_pem", models.TextField()),
                ("public_key_pem", models.TextField()),
                ("public_key_fingerprint", models.CharField(db_index=True, max_length=64)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "holder",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="keypair",
                        to="holder_app.holderprofile",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="walletcredential",
            name="holder",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="holder_app.holderprofile",
            ),
        ),
    ]
