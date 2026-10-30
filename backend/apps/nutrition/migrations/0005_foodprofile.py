from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("nutrition", "0004_foodalias"),
    ]

    operations = [
        migrations.CreateModel(
            name="FoodProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("course", models.CharField(default="any", max_length=16)),
                ("region", models.CharField(default="any", max_length=16)),
                ("diet_class", models.CharField(default="veg", max_length=16)),
                ("is_sweet", models.BooleanField(default=False)),
                ("is_fried", models.BooleanField(default=False)),
                ("cuisine_tags", models.JSONField(blank=True, default=list)),
                (
                    "food",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to="nutrition.food",
                    ),
                ),
            ],
        ),
    ]
