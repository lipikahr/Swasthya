from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0002_food_preferences"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="appearance",
            field=models.CharField(blank=True, default="system", max_length=16),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="autoplay_replies",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="likes",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="notes",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="restrictions",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
