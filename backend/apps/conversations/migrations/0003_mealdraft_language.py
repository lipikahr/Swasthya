from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("conversations", "0002_mealdraft"),
    ]

    operations = [
        migrations.AddField(
            model_name="mealdraft",
            name="language",
            field=models.CharField(blank=True, max_length=16),
        ),
        migrations.AddField(
            model_name="mealdraft",
            name="original_text",
            field=models.TextField(blank=True, default=""),
        ),
    ]
