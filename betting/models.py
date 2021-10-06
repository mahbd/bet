from typing import Union

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from betting.choices import GAME_CHOICES, DEPOSIT_CHOICES, DEPOSIT_SOURCE_CHOICES, STATUS_PENDING, STATUS_CHOICES, \
    STATUS_AWAITING_RESULT, MATCH_STATUS_CHOICES, STATUS_HIDDEN, STATUS_LOCKED, METHOD_TYPE_CHOICES, \
    METHOD_TYPE_PERSONAL, STATUS_CLOSED, SOURCE_BANK
from users.models import User, Club

default_configs = {
    'min_balance': 10,
    'limit_deposit': 1,
    'min_deposit': 100,
    'max_deposit': 25000,
    'limit_withdraw': 1,
    'min_withdraw': 500,
    'max_withdraw': 25000,
    'limit_transfer': 1,
    'min_transfer': 10,
    'max_transfer': 25000,
    'limit_bet': 50,
    'min_bet': 10,
    'max_bet': 25000,
    'refer_commission': 0.5,
    'disable_club_transfer': 0,
    'disable_user_transfer': 0,
    'disable_deposit': 0,
    'disable_withdraw': 0,
    'deposit_waiting_time': 15,
}


def club_validator(sender: User, receiver: User):
    if sender.user_club != receiver.user_club:
        raise ValidationError("Transaction outside club is not allowed.")
    try:
        sender_admin = bool(sender.club)
    except Club.DoesNotExist:
        sender_admin = False
    try:
        receiver_admin = bool(receiver.club)
    except Club.DoesNotExist:
        receiver_admin = False

    if not sender_admin and not receiver_admin:
        raise ValidationError("Transaction can not be done between regular users.")
    if not receiver:
        raise ValidationError("Recipients is not selected")


def club_admin_withdraw_validator(user: User):
    if not user.is_club_admin():
        raise ValidationError("Only club admin can withdraw club balance.")


def user_balance_validator(user: Union[User, Club], amount):
    if user.balance < amount:
        raise ValidationError('User does not have enough balance.')


def bet_question_validator(bet_question):
    if isinstance(bet_question, int):
        bet_question = BetQuestion.objects.filter(id=bet_question)
        if bet_question:
            bet_question = bet_question[0]
        else:
            raise ValidationError('Wrong bet scope id!')
    if bet_question.is_locked():
        raise ValidationError('This bet_scope is locked!')


class Announcement(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    expired = models.BooleanField()
    text = models.TextField()


class ConfigModel(models.Model):
    description = models.TextField(blank=True, null=True)
    name = models.CharField(max_length=255, unique=True, primary_key=True)
    value = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'Configuration'
        verbose_name_plural = 'Configurations'
        ordering = ('name',)


class Match(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    game_name = models.CharField(max_length=255, choices=GAME_CHOICES, help_text="name of the game")
    score = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, choices=MATCH_STATUS_CHOICES, default=STATUS_HIDDEN)
    start_time = models.DateTimeField(default=timezone.now, blank=True, null=True)
    team_a_name = models.CharField(max_length=255)
    team_b_name = models.CharField(max_length=255)
    team_a_color = models.CharField(max_length=255, blank=True, null=True)
    team_b_color = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'{self.team_a_name} vs {self.team_b_name}'

    class Meta:
        ordering = ['-created_at']


class QuestionOption(models.Model):
    option = models.CharField(max_length=255)
    rate = models.FloatField(default=1)
    hidden = models.BooleanField(default=False)
    limit = models.IntegerField(default=10_000_000)


class BetQuestion(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    options = models.ManyToManyField(QuestionOption, help_text="Question options for user")
    question = models.CharField(max_length=1023, help_text="Question of bet")
    status = models.CharField(max_length=255, choices=MATCH_STATUS_CHOICES, default=STATUS_HIDDEN)
    winner = models.ForeignKey(QuestionOption, on_delete=models.CASCADE, blank=True, null=True, related_name='gnn',
                               help_text="Winner option id")
    created_at = models.DateTimeField(auto_now_add=True)

    def is_locked(self):
        disabled = [STATUS_LOCKED, STATUS_CLOSED]
        return self.status in disabled or self.match.status in disabled or self.winner

    def __str__(self):
        return f'{self.question}'

    class Meta:
        verbose_name_plural = 'Bet Options'
        ordering = ['-created_at']


class Bet(models.Model):
    amount = models.IntegerField(help_text='How much he/she bet')
    bet_question = models.ForeignKey(BetQuestion, on_delete=models.PROTECT, validators=[bet_question_validator],
                                     help_text="For which question bet is done")
    choice = models.ForeignKey(QuestionOption, help_text="Choice for question", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, help_text="Time when bet is created")
    is_winner = models.BooleanField(default=None, blank=True, null=True, help_text="If this bet is winner")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AWAITING_RESULT)
    win_rate = models.FloatField(default=1.00, blank=True, null=True, help_text="Multiplication with bet amount")
    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text="User id who betting")
    user_balance = models.FloatField(default=0.0, help_text="User balance after bet")
    win_amount = models.FloatField(default=0, help_text='How much will get if wins')

    class Meta:
        ordering = ['bet_question', '-created_at']


class DepositMethod(models.Model):
    convert_rate = models.FloatField(default=1.00)
    method = models.CharField(max_length=255, choices=DEPOSIT_CHOICES[:8])
    method_type = models.CharField(max_length=255, choices=METHOD_TYPE_CHOICES, default=METHOD_TYPE_PERSONAL)
    number1 = models.CharField(max_length=32)
    number2 = models.CharField(max_length=32, null=True, blank=True)

    class Meta:
        verbose_name = 'Method'
        verbose_name_plural = 'Method List'


class Deposit(models.Model):
    amount = models.FloatField(help_text="how much money transacted in 2 point precession decimal number")
    balance = models.FloatField(default=0, blank=True, null=True)
    club = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deposit_source = models.CharField(max_length=50, choices=DEPOSIT_SOURCE_CHOICES, default=SOURCE_BANK,
                                      help_text="Options are, commission|bank|refer")
    method = models.CharField(max_length=50, choices=DEPOSIT_CHOICES)
    site_account = models.CharField(max_length=255, blank=True, null=True)
    reference = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    user_account = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    class Meta:
        ordering = ['-created_at']


class Transfer(models.Model):
    amount = models.FloatField(help_text="how much money transacted in 2 point precession decimal number")
    balance = models.FloatField(default=0, blank=True, null=True, help_text="User balance after transfer")
    club = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, blank=True,
                             help_text="Club Id from which money is going to be transferred")
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True, help_text="Description of transfer")
    recipient = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recipients',
                                  help_text="User id to whom money transferred")
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, help_text="User id of transaction maker")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    class Meta:
        ordering = ['-created_at']


class Withdraw(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, help_text="User id of transaction maker")
    method = models.CharField(max_length=50, choices=DEPOSIT_CHOICES,
                              help_text="method used to do transaction")
    amount = models.FloatField(help_text="how much money transacted in 2 point precession decimal number")
    user_account = models.CharField(max_length=255, blank=True, null=True,
                                    help_text="bank account number. Used for deposit and withdraw")
    site_account = models.CharField(max_length=255, blank=True, null=True,
                                    help_text="bank account number of the website")
    reference = models.CharField(max_length=255, blank=True, null=True)
    balance = models.FloatField(default=0, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        ordering = ['-created_at']
