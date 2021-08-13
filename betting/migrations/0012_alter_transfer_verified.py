# Generated by Django 3.2.6 on 2021-08-13 11:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('betting', '0011_auto_20210813_1736'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transfer',
            name='verified',
            field=models.BooleanField(blank=True, default=None, help_text='Status if admin had verified. After verification(for deposit), user account will be deposited', null=True),
        ),
    ]
