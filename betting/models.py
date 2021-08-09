from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from users.models import User, Club

TYPE_DEPOSIT = 'deposit'
TYPE_WITHDRAW = 'withdraw'
METHOD_BET = 'bet'
METHOD_BET_ODD = 'bet_odd'
METHOD_BET_EVEN = 'bet_even'
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
    (METHOD_BKASH, 'bKash'),
    (METHOD_ROCKET, 'DBBL Rocket'),
    (METHOD_SURECASH, 'Nagad'),
    (METHOD_UPAY, 'Upay'),
    (METHOD_MCASH, 'Mcash'),
    (METHOD_MYCASH, 'My Cash'),
    (METHOD_SURECASH, 'Sure Cash'),
    (METHOD_TRUSTPAY, 'Trust Axiata Pay'),
    (METHOD_BET, 'Bet'),
    (METHOD_BET_ODD, 'Odd bet id'),
    (METHOD_BET_EVEN, 'Even bet id'),
    (METHOD_TRANSFER, 'Transfer money'),
)
CHOICE_FIRST = 'option_1'
CHOICE_SECOND = 'option_2'
CHOICE_THIRD = 'option_3'
CHOICE_FOURTH = 'option_4'
BET_CHOICES = (
    (CHOICE_FIRST, 'Option 1'),
    (CHOICE_SECOND, 'Option 2'),
    (CHOICE_THIRD, 'Option 3'),
    (CHOICE_FOURTH, 'Option 4')
)

GAME_FOOTBALL = 'football'
GAME_CRICKET = 'cricket'
GAME_TENNIS = 'tennis'
GAME_OTHERS = 'others'
GAME_CHOICES = (
    (GAME_FOOTBALL, 'Football'),
    (GAME_CRICKET, 'Cricket'),
    (GAME_TENNIS, 'Tennis'),
    (GAME_OTHERS, 'Others')
)


def club_validator(sender: User, t_type, method, receiver: User):
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


def user_balance_validator(user: User, amount, t_type):
    if t_type == TYPE_WITHDRAW:
        if user.balance < amount:
            raise ValidationError('User does not have enough balance.')


def bet_scope_validator(bet_scope):
    if isinstance(bet_scope, int):
        bet_scope = BetScope.objects.filter(id=bet_scope)
        if bet_scope:
            bet_scope = bet_scope[0]
        else:
            raise ValidationError('Wrong bet scope id!')
    if bet_scope.is_locked():
        raise ValidationError('Currently bet is not allowed here!')


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
    created_at = models.DateTimeField(default=timezone.now)

    def clean(self):
        club_validator(self.user, self.type, self.method, self.to)
        user_balance_validator(self.user, self.amount, self.type)
        super().clean()

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.full_clean()
        super().save(force_insert, force_update, using, update_fields)

    def __str__(self):
        return str(self.id)

    class Meta:
        ordering = ['-created_at']


class Option(models.Model):
    name = models.CharField(max_length=255)
    rate = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                               validators=[validators.MinValueValidator(0)])


class Match(models.Model):
    game_name = models.CharField(max_length=255, choices=GAME_CHOICES)
    title = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    def __str__(self):
        return f'{self.title} {self.start_time.strftime("%d %b %y")}'

    class Meta:
        ordering = ['-end_time', '-start_time', 'game_name']


class BetScope(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    question = models.CharField(max_length=1023)

    option_1 = models.CharField(max_length=255)
    option_1_rate = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        validators=[validators.MinValueValidator(0)])
    option_2 = models.CharField(max_length=255)
    option_2_rate = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        validators=[validators.MinValueValidator(0)])
    option_3 = models.CharField(max_length=255, blank=True, null=True)
    option_3_rate = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        validators=[validators.MinValueValidator(0)],
                                        blank=True, null=True)
    option_4 = models.CharField(max_length=255, blank=True, null=True)
    option_4_rate = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        validators=[validators.MinValueValidator(0)],
                                        blank=True, null=True)
    winner = models.CharField(max_length=255, choices=BET_CHOICES, blank=True, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    locked = models.BooleanField(default=False)
    processed_internally = models.BooleanField(default=False)

    def is_locked(self):
        return bool(
            self.locked or self.winner or self.end_time <= timezone.now() or self.match.end_time <= timezone.now())

    def __str__(self):
        return f'{self.match.title} {self.question} {not self.is_locked()} {self.start_time.strftime("%d %b %y")}'

    class Meta:
        ordering = ['-end_time']


class Bet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bet_scope = models.ForeignKey(BetScope, on_delete=models.PROTECT, validators=[bet_scope_validator])
    choice = models.CharField(max_length=10, choices=BET_CHOICES)
    amount = models.IntegerField(help_text='How much he bet')
    status = models.CharField(max_length=255, default='No result', help_text='Result of the bet. Win/Loss')
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        user_balance_validator(self.user, self.amount, TYPE_WITHDRAW)
        super().clean()

    class Meta:
        ordering = ['bet_scope', '-created_at']
