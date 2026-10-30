from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("meals", "0002_userfood_and_dayplan"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="plannedslot",
            name="one_slot_per_day_plan",
        ),
        migrations.AddField(
            model_name="plannedslot",
            name="label",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="plannedslot",
            name="position",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="plannedslot",
            name="source",
            field=models.CharField(
                choices=[("generated", "Generated"), ("manual", "Manual"), ("liked", "Liked")],
                default="generated",
                max_length=16,
            ),
        ),
        migrations.AlterModelOptions(
            name="plannedslot",
            options={"ordering": ["slot", "position", "id"]},
        ),
        migrations.AddIndex(
            model_name="plannedslot",
            index=models.Index(fields=["plan", "slot"], name="meals_plann_plan_id_slot_idx"),
        ),
    ]
