# Generated by Django 3.2.6 on 2021-08-17 21:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('betting', '0002_auto_20210817_0720'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bet',
            name='status',
        ),
        migrations.AddField(
            model_name='bet',
            name='answer',
            field=models.CharField(blank=True, default='Unknown', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='bet',
            name='is_winner',
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='bet',
            name='return_rate',
            field=models.FloatField(blank=True, default=1.0, null=True),
        ),
    ]
