# Generated by Django 3.2.6 on 2021-08-07 11:37

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20210807_1009'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='balance',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15, validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]