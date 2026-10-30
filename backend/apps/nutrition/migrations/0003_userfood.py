import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("nutrition", "0002_foodembedding"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserFood",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("ingredients", models.TextField(blank=True, default="")),
                ("serving_amount", models.DecimalField(decimal_places=3, max_digits=12)),
                ("serving_unit", models.CharField(max_length=64)),
                ("energy_kcal", models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True)),
                ("protein_g", models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True)),
                ("carb_g", models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True)),
                ("fat_g", models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True)),
                ("fibre_g", models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True)),
                ("nutrition_source", models.CharField(default="user_provided", max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_foods",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["name", "id"]},
        ),
    ]
