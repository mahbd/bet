# Generated by Django 3.2.7 on 2021-10-05 04:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('betting', '0004_rename_user_balance_withdraw_balance'),
    ]

    operations = [
        migrations.RenameField(
            model_name='match',
            old_name='hide',
            new_name='hidden',
        ),
    ]
