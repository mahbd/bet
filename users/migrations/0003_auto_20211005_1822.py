# Generated by Django 3.2.7 on 2021-10-05 12:22

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_club_username'),
    ]

    operations = [
        migrations.AlterField(
            model_name='club',
            name='balance',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='club',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='user',
            name='balance',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='user',
            name='game_editor',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='user',
            name='referred_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='refer_set', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='user',
            name='user_club',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.club'),
        ),
    ]
