# Generated by Django 3.2.6 on 2021-10-04 04:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='club',
            name='username',
            field=models.CharField(max_length=255, unique=True),
        ),
    ]