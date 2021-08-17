# Generated by Django 3.2.6 on 2021-08-17 00:34

import betting.models
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('expired', models.BooleanField()),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='ConfigModel',
            fields=[
                ('name', models.CharField(max_length=255, primary_key=True, serialize=False, unique=True)),
                ('value', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Configuration',
                'verbose_name_plural': 'Configurations',
            },
        ),
        migrations.CreateModel(
            name='DepositWithdrawMethod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(choices=[('bkash', 'bKash'), ('rocket', 'DBBL Rocket'), ('nagad', 'Nagad'), ('upay', 'Upay'), ('mcash', 'Mcash'), ('mycash', 'My Cash'), ('surecash', 'Sure Cash'), ('trustpay', 'Trust Axiata Pay')], help_text='hidden method code for internal processing', max_length=255, unique=True)),
                ('name', models.CharField(help_text='Method name to be shown to users', max_length=255)),
                ('number1', models.CharField(blank=True, default='017331245546', max_length=32, null=True)),
                ('number2', models.CharField(blank=True, default='019455422145', max_length=32, null=True)),
            ],
            options={
                'verbose_name': 'Method',
                'verbose_name_plural': 'Method List',
            },
        ),
        migrations.CreateModel(
            name='Match',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('game_name', models.CharField(choices=[('football', 'Football'), ('cricket', 'Cricket'), ('tennis', 'Tennis'), ('others', 'Others')], help_text='name of the game', max_length=255)),
                ('title', models.CharField(help_text='title of the match. eg: Canada vs USA', max_length=255)),
                ('locked', models.BooleanField(default=False)),
                ('start_time', models.DateTimeField(default=django.utils.timezone.now, help_text='When match will be unlocked for betting.')),
                ('end_time', models.DateTimeField(help_text='When match will be locked for betting.')),
            ],
            options={
                'ordering': ['-end_time', '-start_time', 'game_name'],
            },
        ),
        migrations.CreateModel(
            name='Withdraw',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('method', models.CharField(choices=[('bkash', 'bKash'), ('rocket', 'DBBL Rocket'), ('nagad', 'Nagad'), ('upay', 'Upay'), ('mcash', 'Mcash'), ('mycash', 'My Cash'), ('surecash', 'Sure Cash'), ('trustpay', 'Trust Axiata Pay'), ('club', 'Club W/D')], help_text='method used to do transaction', max_length=50)),
                ('amount', models.FloatField(help_text='how much money transacted in 2 point precession decimal number', validators=[django.core.validators.MinValueValidator(1)])),
                ('account', models.CharField(blank=True, help_text='bank account number. Used for deposit and withdraw', max_length=255, null=True)),
                ('superuser_account', models.CharField(blank=True, help_text='bank account number of the superuser', max_length=255, null=True)),
                ('transaction_id', models.CharField(blank=True, max_length=255, null=True)),
                ('user_balance', models.FloatField(default=0)),
                ('description', models.TextField(blank=True, null=True)),
                ('verified', models.BooleanField(blank=True, default=None, help_text='Status if admin had verified. After verification(for deposit), user account will be deposited', null=True)),
                ('processed_internally', models.BooleanField(default=False, editable=False, help_text='For internal uses only')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(help_text='User id of transaction maker', null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Transfer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.FloatField(help_text='how much money transacted in 2 point precession decimal number', validators=[django.core.validators.MinValueValidator(1)])),
                ('user_balance', models.FloatField(default=0)),
                ('description', models.TextField(blank=True, null=True)),
                ('verified', models.BooleanField(blank=True, default=None, help_text='Status if admin had verified. After verification(for deposit), user account will be deposited', null=True)),
                ('processed_internally', models.BooleanField(default=False, editable=False, help_text='For internal uses only')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('to', models.ForeignKey(help_text='User id to whom money transferred', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recipients', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(help_text='User id of transaction maker', null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Deposit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('method', models.CharField(choices=[('bkash', 'bKash'), ('rocket', 'DBBL Rocket'), ('nagad', 'Nagad'), ('upay', 'Upay'), ('mcash', 'Mcash'), ('mycash', 'My Cash'), ('surecash', 'Sure Cash'), ('trustpay', 'Trust Axiata Pay'), ('club', 'Club W/D')], help_text='method used to do transaction', max_length=50)),
                ('amount', models.FloatField(help_text='how much money transacted in 2 point precession decimal number', validators=[django.core.validators.MinValueValidator(1)])),
                ('account', models.CharField(blank=True, help_text='bank account number. Used for deposit and withdraw', max_length=255, null=True)),
                ('transaction_id', models.CharField(blank=True, max_length=255, null=True)),
                ('user_balance', models.FloatField(default=0)),
                ('superuser_account', models.CharField(blank=True, help_text='bank account number of the superuser', max_length=255, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('verified', models.BooleanField(blank=True, default=None, help_text='Status if admin had verified. After verification(for deposit), user account will be deposited', null=True)),
                ('processed_internally', models.BooleanField(default=False, editable=False, help_text='For internal uses only')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('user', models.ForeignKey(help_text='User id of transaction maker', null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BetScope',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(help_text='Question of bet', max_length=1023)),
                ('option_1', models.CharField(max_length=255)),
                ('option_1_rate', models.FloatField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('option_2', models.CharField(max_length=255)),
                ('option_2_rate', models.FloatField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('option_3', models.CharField(blank=True, max_length=255, null=True)),
                ('option_3_rate', models.FloatField(blank=True, default=1, null=True, validators=[django.core.validators.MinValueValidator(1)])),
                ('option_4', models.CharField(blank=True, max_length=255, null=True)),
                ('option_4_rate', models.FloatField(blank=True, default=1, null=True, validators=[django.core.validators.MinValueValidator(1)])),
                ('winner', models.CharField(blank=True, choices=[('option_1', 'Option 1'), ('option_2', 'Option 2'), ('option_3', 'Option 3'), ('option_4', 'Option 4')], help_text='Which option is the winner. Be careful. As soon as you select winner, bet winner receive money. This can not be reverted', max_length=255, null=True)),
                ('start_time', models.DateTimeField(blank=True, default=django.utils.timezone.now, help_text='when this question will be available for bet', null=True)),
                ('end_time', models.DateTimeField(blank=True, help_text='when this question will no longer accept bet', null=True)),
                ('locked', models.BooleanField(default=False, help_text='manually lock question before end_time')),
                ('processed_internally', models.BooleanField(default=False)),
                ('match', models.ForeignKey(help_text='Id of the match under which this is question', on_delete=django.db.models.deletion.CASCADE, to='betting.match')),
            ],
            options={
                'verbose_name_plural': 'Bet Options',
                'ordering': ['-end_time'],
            },
        ),
        migrations.CreateModel(
            name='Bet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('choice', models.CharField(choices=[('option_1', 'Option 1'), ('option_2', 'Option 2'), ('option_3', 'Option 3'), ('option_4', 'Option 4')], help_text='List of bet choices', max_length=10)),
                ('amount', models.IntegerField(help_text='How much he bet')),
                ('winning', models.FloatField(default=0, help_text='How much will get if wins')),
                ('paid', models.BooleanField(default=False)),
                ('status', models.CharField(default='No result', help_text='Result of the bet. Win/Loss', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('bet_scope', models.ForeignKey(help_text='For which question bet is done', on_delete=django.db.models.deletion.PROTECT, to='betting.betscope', validators=[betting.models.bet_scope_validator])),
                ('user', models.ForeignKey(help_text='User id who betting', on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['bet_scope', '-created_at'],
            },
        ),
    ]
