# Generated by Django 3.2.6 on 2021-08-08 02:39

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('betting', '0011_auto_20210807_2351'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='draw_ratio',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name='game',
            name='first_ratio',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name='game',
            name='second_ratio',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15, validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]
