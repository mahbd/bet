# Generated by Django 3.2.7 on 2021-10-11 04:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_club_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'ordering': ('balance',)},
        ),
    ]
