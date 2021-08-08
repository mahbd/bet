from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from users.models import User, Club

TYPE_DEPOSIT = 'deposit'
TYPE_WITHDRAW = 'withdraw'
METHOD_BET = 'bet'
METHOD_TRANSFER = 'transfer'
METHOD_BKASH = 'bkash'
METHOD_ROCKET = 'rocket'
METHOD_NAGAD = 'nagad'
METHOD_UPAY = 'upay'
METHOD_MCASH = 'mcash'
METHOD_MYCASH = 'mycash'
METHOD_SURECASH = 'surecash'
METHOD_TRUSTPAY = 'trustpay'

DEPOSIT_WITHDRAW_CHOICES = (
    (METHOD_BET, 'Bet'),
    (METHOD_TRANSFER, 'Transfer money'),
    (METHOD_BKASH, 'bKash'),
    (METHOD_ROCKET, 'DBBL Rocket'),
    (METHOD_SURECASH, 'Nagad'),
    (METHOD_UPAY, 'Upay'),
    (METHOD_MCASH, 'Mcash'),
    (METHOD_MYCASH, 'My Cash'),
    (METHOD_SURECASH, 'Sure Cash'),
    (METHOD_TRUSTPAY, 'Trust Axiata Pay')
)
CHOICE_FIRST = 'first'
CHOICE_SECOND = 'second'
CHOICE_DRAW = 'draw'


def validate_receiver(sender: User, t_type, method, receiver: User):
    if t_type == TYPE_WITHDRAW and method == METHOD_TRANSFER:
        if sender.user_club != receiver.user_club:
            raise ValidationError("Transaction outside club is not allowed")

        try:
            sender_admin = bool(sender.club)
        except Club.DoesNotExist:
            sender_admin = False
        try:
            receiver_admin = bool(receiver.club)
        except Club.DoesNotExist:
            receiver_admin = False

        if not sender_admin and not receiver_admin:
            raise ValidationError("Transaction can not be done between regular users")
        if not receiver:
            raise ValidationError("Recipients is not selected")


def validate_amount(user: User, amount, t_type):
    if t_type == TYPE_WITHDRAW:
        if user.balance < amount:
            raise ValidationError('User does not have enough balance.')


class DepositWithdrawMethod(models.Model):
    code = models.CharField(max_length=255, choices=DEPOSIT_WITHDRAW_CHOICES, unique=True)
    name = models.CharField(max_length=255)


class Transaction(models.Model):
    TYPE_CHOICES = (
        (TYPE_DEPOSIT, 'Deposit'),
        (TYPE_WITHDRAW, 'Withdrawal')
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    method = models.CharField(max_length=50, choices=DEPOSIT_WITHDRAW_CHOICES)
    to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recipients')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    account = models.CharField(max_length=255, blank=True, null=True)
    verified = models.BooleanField(default=False)
    processed_internally = models.BooleanField(default=False, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        validate_receiver(self.user, self.type, self.method, self.to)
        validate_amount(self.user, self.amount, TYPE_WITHDRAW)
        super().clean()

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.full_clean()
        super().save(force_insert, force_update, using, update_fields)

    def __str__(self):
        return str(self.id)

    class Meta:
        ordering = ['-created_at']


class Game(models.Model):
    GAME_CHOICES = (
        (CHOICE_FIRST, 'First'),
        (CHOICE_DRAW, 'Draw'),
        (CHOICE_SECOND, 'Second'),
    )
    name = models.CharField(max_length=255)
    first = models.CharField(max_length=255)
    second = models.CharField(max_length=255)
    start = models.DateTimeField()
    end = models.DateTimeField()
    winner = models.CharField(max_length=10, choices=GAME_CHOICES, blank=True, null=True)
    locked = models.BooleanField(default=False)

    first_ratio = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                      validators=[validators.MinValueValidator(0)])
    second_ratio = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                       validators=[validators.MinValueValidator(0)])
    draw_ratio = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                     validators=[validators.MinValueValidator(0)])
    processed_internally = models.BooleanField(default=False, editable=False)

    def time_locked(self):
        return self.winner or self.end <= timezone.now()

    def __str__(self):
        return f'{self.first} vs {self.second} ({self.name})'


def validate_game(game: Game):
    if game.locked or game.time_locked():
        raise ValidationError('Bet is not allowed on this game!')


class Bet(models.Model):
    GAME_CHOICES = (
        (CHOICE_FIRST, 'First'),
        (CHOICE_DRAW, 'Draw'),
        (CHOICE_SECOND, 'Second'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.PROTECT, validators=[validate_game])
    choice = models.CharField(max_length=10, choices=GAME_CHOICES)
    amount = models.IntegerField()
    status = models.CharField(max_length=255, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['game', '-created_at']
