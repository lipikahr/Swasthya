import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("meals", "0001_initial"),
        ("nutrition", "0003_userfood"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="mealitem",
            name="food",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="meal_items",
                to="nutrition.food",
            ),
        ),
        migrations.AddField(
            model_name="mealitem",
            name="user_food",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="meal_items",
                to="nutrition.userfood",
            ),
        ),
        migrations.CreateModel(
            name="DayPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="day_plans",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-date"]},
        ),
        migrations.AddConstraint(
            model_name="dayplan",
            constraint=models.UniqueConstraint(fields=("user", "date"), name="one_day_plan_per_user_date"),
        ),
        migrations.CreateModel(
            name="PlannedSlot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slot", models.CharField(choices=[("breakfast", "Breakfast"), ("lunch", "Lunch"), ("snack", "Snack"), ("dinner", "Dinner")], max_length=16)),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=12)),
                ("unit", models.CharField(max_length=64)),
                ("nutrition_snapshot", models.JSONField(default=dict)),
                ("status", models.CharField(choices=[("planned", "Planned"), ("swapped", "Swapped"), ("logged", "Logged")], default="planned", max_length=16)),
                ("food", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="nutrition.food")),
                ("user_food", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="nutrition.userfood")),
                ("logged_meal", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="meals.meal")),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="slots", to="meals.dayplan")),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.AddConstraint(
            model_name="plannedslot",
            constraint=models.UniqueConstraint(fields=("plan", "slot"), name="one_slot_per_day_plan"),
        ),
    ]
