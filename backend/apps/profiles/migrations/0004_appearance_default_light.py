from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0003_settings_preferences"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="appearance",
            field=models.CharField(blank=True, default="light", max_length=16),
        ),
    ]
