from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from bet.settings import MINIMUM_TRANSACTION
from users.models import User, Club

TYPE_DEPOSIT = 'deposit'
TYPE_WITHDRAW = 'withdraw'
METHOD_TRANSFER = 'transfer'
METHOD_BKASH = 'bkash'
METHOD_ROCKET = 'rocket'
METHOD_NAGAD = 'nagad'
METHOD_UPAY = 'upay'
METHOD_MCASH = 'mcash'
METHOD_MYCASH = 'mycash'
METHOD_SURECASH = 'surecash'
METHOD_TRUSTPAY = 'trustpay'
METHOD_BET = 'bet'
METHOD_BET_ODD = 'bet_odd'
METHOD_BET_EVEN = 'bet_even'
METHOD_CLUB = 'club'

DEPOSIT_WITHDRAW_CHOICES = (
    (METHOD_BKASH, 'bKash'),
    (METHOD_ROCKET, 'DBBL Rocket'),
    (METHOD_NAGAD, 'Nagad'),
    (METHOD_UPAY, 'Upay'),
    (METHOD_MCASH, 'Mcash'),
    (METHOD_MYCASH, 'My Cash'),
    (METHOD_SURECASH, 'Sure Cash'),
    (METHOD_TRUSTPAY, 'Trust Axiata Pay'),
    (METHOD_BET, 'Bet'),
    (METHOD_BET_ODD, 'Odd bet id'),
    (METHOD_BET_EVEN, 'Even bet id'),
    (METHOD_TRANSFER, 'Transfer'),
    (METHOD_CLUB, 'Club withdraw'),
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


def user_balance_validator(user: User, amount, method=None):
    if method == METHOD_CLUB and user.club.balance < amount:
        raise ValidationError('Club do not have enough balance.')
    elif user.balance < amount:
        raise ValidationError('User does not have enough balance.')


def bet_scope_validator(bet_scope):
    if isinstance(bet_scope, int):
        bet_scope = BetScope.objects.filter(id=bet_scope)
        if bet_scope:
            bet_scope = bet_scope[0]
        else:
            raise ValidationError('Wrong bet scope id!')
    if bet_scope.is_locked():
        raise ValidationError('This bet_scope is locked!')


class DepositWithdrawMethod(models.Model):
    code = models.CharField(max_length=255, choices=DEPOSIT_WITHDRAW_CHOICES[:8], unique=True,
                            help_text="hidden method code for internal processing")
    name = models.CharField(max_length=255, help_text="Method name to be shown to users")
    number1 = models.CharField(default="017331245546", max_length=32, null=True, blank=True)
    number2 = models.CharField(default="019455422145", max_length=32, null=True, blank=True)

    class Meta:
        verbose_name = 'Method'
        verbose_name_plural = 'Method List'


class Match(models.Model):
    game_name = models.CharField(max_length=255, choices=GAME_CHOICES, help_text="name of the game")
    title = models.CharField(max_length=255, help_text="title of the match. eg: Canada vs USA")
    locked = models.BooleanField(default=False)
    start_time = models.DateTimeField(help_text="When match will be unlocked for betting.")
    end_time = models.DateTimeField(help_text="When match will be locked for betting.")

    def is_live(self):
        return not self.locked and self.start_time >= timezone.now() >= self.end_time

    def is_locked(self):
        return self.locked or self.end_time < timezone.now()

    def __str__(self):
        return f'{self.title} {self.start_time.strftime("%d %b %y")}'

    class Meta:
        ordering = ['-end_time', '-start_time', 'game_name']


class BetScope(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, help_text="Id of the match under which this is question")
    question = models.CharField(max_length=1023, help_text="Question of bet")

    option_1 = models.CharField(max_length=255)
    option_1_rate = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        validators=[MinValueValidator(0)])
    option_2 = models.CharField(max_length=255)
    option_2_rate = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        validators=[MinValueValidator(0)])
    option_3 = models.CharField(max_length=255, blank=True, null=True)
    option_3_rate = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        validators=[MinValueValidator(0)],
                                        blank=True, null=True)
    option_4 = models.CharField(max_length=255, blank=True, null=True)
    option_4_rate = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        validators=[MinValueValidator(0)],
                                        blank=True, null=True)
    winner = models.CharField(max_length=255, choices=BET_CHOICES, blank=True, null=True,
                              help_text="Which option is the winner. Be careful. As soon as you select winner,"
                                        " bet winner receive money. This can not be reverted")
    start_time = models.DateTimeField(help_text="when this question will be available for bet", blank=True, null=True)
    end_time = models.DateTimeField(help_text="when this question will no longer accept bet", blank=True, null=True)
    locked = models.BooleanField(default=False, help_text="manually lock question before end_time")
    processed_internally = models.BooleanField(default=False)

    def is_locked(self):
        return bool(
            self.locked or self.match.locked or self.winner or (
                    self.end_time and self.end_time <= timezone.now()) or self.match.end_time <= timezone.now())

    def __str__(self):
        return f'{self.match.title} {self.question} {not self.is_locked()}'

    class Meta:
        verbose_name_plural = 'Bet Options'
        ordering = ['-end_time']


class Bet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text="User id who betting")
    bet_scope = models.ForeignKey(BetScope, on_delete=models.PROTECT, validators=[bet_scope_validator],
                                  help_text="For which question bet is done")
    choice = models.CharField(max_length=10, choices=BET_CHOICES, help_text="List of bet choices")
    amount = models.IntegerField(help_text='How much he bet')
    status = models.CharField(max_length=255, default='No result', help_text='Result of the bet. Win/Loss')
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        user_balance_validator(self.user, self.amount)
        super().clean()

    class Meta:
        ordering = ['bet_scope', '-created_at']


class Announcement(models.Model):
    text = models.TextField()
    expired = models.BooleanField()
    created_at = models.DateTimeField(default=timezone.now)


class Deposit(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, help_text="User id of transaction maker")
    method = models.CharField(max_length=50, choices=DEPOSIT_WITHDRAW_CHOICES,
                              help_text="method used to do transaction")
    amount = models.FloatField(validators=[MinValueValidator(MINIMUM_TRANSACTION)],
                               help_text="how much money transacted in 2 point precession decimal number")
    account = models.CharField(max_length=255, blank=True, null=True,
                               help_text="bank account number. Used for deposit and withdraw")
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    superuser_account = models.CharField(max_length=255, blank=True, null=True,
                                         help_text="bank account number of the superuser")
    description = models.TextField(blank=True, null=True)
    verified = models.BooleanField(default=None, null=True, blank=True,
                                   help_text="Status if admin had verified. After verification(for deposit), "
                                             "user account will be deposited")
    processed_internally = models.BooleanField(default=False, editable=False, help_text="For internal uses only")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return str(self.id)

    class Meta:
        ordering = ['-created_at']


class Withdraw(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, help_text="User id of transaction maker")
    method = models.CharField(max_length=50, choices=DEPOSIT_WITHDRAW_CHOICES,
                              help_text="method used to do transaction")
    amount = models.FloatField(validators=[MinValueValidator(MINIMUM_TRANSACTION)],
                               help_text="how much money transacted in 2 point precession decimal number")
    account = models.CharField(max_length=255, blank=True, null=True,
                               help_text="bank account number. Used for deposit and withdraw")
    superuser_account = models.CharField(max_length=255, blank=True, null=True,
                                         help_text="bank account number of the superuser")
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    verified = models.BooleanField(default=None, null=True, blank=True,
                                   help_text="Status if admin had verified. After verification(for deposit), "
                                             "user account will be deposited")
    processed_internally = models.BooleanField(default=False, editable=False, help_text="For internal uses only")
    created_at = models.DateTimeField(default=timezone.now)

    def clean(self):
        user_balance_validator(self.user, self.amount, self.method)
        super().clean()

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.full_clean()
        super().save(force_insert, force_update, using, update_fields)

    def __str__(self):
        return str(self.id)

    class Meta:
        ordering = ['-created_at']


class Transfer(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, help_text="User id of transaction maker")
    to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recipients',
                           help_text="User id to whom money transferred")
    amount = models.FloatField(validators=[MinValueValidator(MINIMUM_TRANSACTION)],
                               help_text="how much money transacted in 2 point precession decimal number")
    description = models.TextField(blank=True, null=True)
    verified = models.BooleanField(default=None, blank=True, null=True,
                                   help_text="Status if admin had verified. After verification(for deposit), "
                                             "user account will be deposited")
    processed_internally = models.BooleanField(default=False, editable=False, help_text="For internal uses only")
    created_at = models.DateTimeField(default=timezone.now)

    def clean(self):
        user_balance_validator(self.user, self.amount)
        club_validator(self.user, self.to)
        super().clean()

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.full_clean()
        super().save(force_insert, force_update, using, update_fields)

    def __str__(self):
        return str(self.id)

    class Meta:
        ordering = ['-created_at']
