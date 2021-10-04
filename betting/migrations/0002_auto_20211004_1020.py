# Generated by Django 3.2.6 on 2021-10-04 04:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('betting', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='announcement',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='deposit',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='deposit',
            name='deposit_source',
            field=models.CharField(choices=[('bank', 'From Bank'), ('refer', 'Referral'), ('commission', 'Club Commission')], default='bank', help_text='Options are, commission|bank|refer', max_length=50),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='withdraw',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
