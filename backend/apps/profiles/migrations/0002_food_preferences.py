from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="allergies",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="allergies_status",
            field=models.CharField(
                blank=True,
                choices=[("", "Not yet provided"), ("none", "No allergies declared"), ("listed", "Allergies listed")],
                default="",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="diet_pattern",
            field=models.CharField(
                blank=True,
                choices=[
                    ("vegetarian", "Vegetarian"),
                    ("vegan", "Vegan"),
                    ("non_vegetarian", "Non-vegetarian"),
                ],
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="dislikes",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="preferred_cuisines",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="preferred_language",
            field=models.CharField(blank=True, default="en", max_length=8),
        ),
    ]
