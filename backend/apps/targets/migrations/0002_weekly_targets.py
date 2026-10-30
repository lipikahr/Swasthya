from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("targets", "0001_initial"),
    ]

    operations = [
        migrations.AddField(model_name="nutritiontarget", name="weekly_calories", field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name="nutritiontarget", name="weekly_carbohydrates_g", field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name="nutritiontarget", name="weekly_fat_g", field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name="nutritiontarget", name="weekly_fibre_g", field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name="nutritiontarget", name="weekly_protein_g", field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
    ]
