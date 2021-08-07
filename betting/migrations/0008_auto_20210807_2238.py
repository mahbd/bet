# Generated by Django 3.2.6 on 2021-08-07 16:38

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('betting', '0007_auto_20210807_2207'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bet',
            options={'ordering': ['game', 'created_at']},
        ),
        migrations.AddField(
            model_name='bet',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]