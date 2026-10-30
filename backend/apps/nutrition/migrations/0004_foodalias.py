from django.db import migrations, models
import django.db.models.deletion


def seed_aliases(apps, schema_editor):
    Food = apps.get_model("nutrition", "Food")
    FoodAlias = apps.get_model("nutrition", "FoodAlias")
    from apps.nutrition.aliases import CURATED_ALIASES
    from apps.nutrition.normalize import normalize_alias

    for food_name, language, alias in CURATED_ALIASES:
        food = Food.objects.filter(food_name__iexact=food_name).order_by("food_code").first()
        if food is None:
            continue
        normalized = normalize_alias(alias)
        if not normalized:
            continue
        FoodAlias.objects.get_or_create(
            food=food,
            language=language,
            normalized_alias=normalized,
            defaults={
                "alias_text": alias,
                "source": "curated",
                "verified": True,
            },
        )


def unseed_aliases(apps, schema_editor):
    FoodAlias = apps.get_model("nutrition", "FoodAlias")
    FoodAlias.objects.filter(source="curated", verified=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("nutrition", "0003_userfood"),
    ]

    operations = [
        migrations.CreateModel(
            name="FoodAlias",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("alias_text", models.CharField(max_length=255)),
                ("language", models.CharField(max_length=16)),
                ("normalized_alias", models.CharField(db_index=True, max_length=255)),
                ("source", models.CharField(choices=[("curated", "Curated"), ("user", "User"), ("model", "Model")], default="curated", max_length=16)),
                ("verified", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "food",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="aliases", to="nutrition.food"),
                ),
            ],
            options={
                "ordering": ["language", "alias_text", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="foodalias",
            constraint=models.UniqueConstraint(
                fields=("food", "normalized_alias", "language"),
                name="unique_food_alias_per_language",
            ),
        ),
        migrations.RunPython(seed_aliases, unseed_aliases),
    ]
