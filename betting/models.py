from typing import Union

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

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
METHOD_CLUB = 'club'
SOURCE_REFER = 'refer'
SOURCE_COMMISSION = 'commission'
SOURCE_BANK = 'bank'

DEPOSIT_SOURCE = (
    (SOURCE_BANK, 'From Bank'),
    (SOURCE_REFER, 'Referral'),
    (SOURCE_COMMISSION, 'Club Commission'),
)

DEPOSIT_WITHDRAW_CHOICES = (
    (METHOD_BKASH, 'bKash'),
    (METHOD_ROCKET, 'DBBL Rocket'),
    (METHOD_NAGAD, 'Nagad'),
    (METHOD_UPAY, 'Upay'),
    (METHOD_MCASH, 'Mcash'),
    (METHOD_MYCASH, 'My Cash'),
    (METHOD_SURECASH, 'Sure Cash'),
    (METHOD_TRUSTPAY, 'Trust Axiata Pay'),
    (METHOD_TRANSFER, 'Transfer'),
    (METHOD_CLUB, 'Club W/D'),
    (SOURCE_COMMISSION, 'Commission'),
    (SOURCE_REFER, 'Referral'),
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

COMMISSION_REFER = 'refer'
COMMISSION_CLUB = 'club'
COMMISSION_CHOICES = (
    (COMMISSION_REFER, 'Refer commission'),
    (COMMISSION_CLUB, 'Club commission'),
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


def user_balance_validator(user: Union[User, Club], amount):
    if user.balance < amount:
        raise ValidationError('User does not have enough balance.')


def bet_scope_validator(bet_scope):
    if isinstance(bet_scope, int):
        bet_scope = BetQuestion.objects.filter(id=bet_scope)
        if bet_scope:
            bet_scope = bet_scope[0]
        else:
            raise ValidationError('Wrong bet scope id!')
    if bet_scope.is_locked():
        raise ValidationError('This bet_scope is locked!')


class Announcement(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
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


class Config:
    def __init__(self):
        self.defaults = {
            'min_balance': 10,
            'limit_deposit': 50,
            'min_deposit': 100,
            'max_deposit': 25000,
            'limit_withdraw': 10,
            'min_withdraw': 500,
            'max_withdraw': 25000,
            'limit_transfer': 50,
            'min_transfer': 10,
            'max_transfer': 25000,
            'limit_bet': 50,
            'min_bet': 10,
            'max_bet': 25000,
            'refer_commission': 0.5,
        }

    def get_from_model(self, name, default=False):
        obj = ConfigModel.objects.filter(name=name)
        if obj:
            return obj[0].value
        else:
            ConfigModel.objects.create(name=name, value=str(default or self.defaults[name]))
            return str(default or self.defaults[name])

    def get_config(self, name):
        return int(self.get_from_model(name))

    def get_config_str(self, name):
        return str(self.get_from_model(name))

    def config_validator(self, user: User, amount, model, des, md=0):
        limit_count = int(self.get_from_model(f'limit_{des}'))
        minimum = int(self.get_from_model(f'min_{des}'))
        maximum = int(self.get_from_model(f'max_{des}'))
        total_per_day = model.objects.filter(user=user,
                                             created_at__gte=timezone.now().replace(hour=0, minute=0,
                                                                                    second=0)).count()
        if total_per_day >= limit_count + md:
            raise ValidationError(f"Maximum limit of {limit_count} per day exceed. {total_per_day}")
        if minimum > amount or amount > maximum:
            raise ValidationError(f"Amount limit of {des} {minimum} - {maximum} does not match. Yours {amount}")


config = Config()


class Match(models.Model):
    end_time = models.DateTimeField(help_text="When match will be locked for betting.")
    game_name = models.CharField(max_length=255, choices=GAME_CHOICES, help_text="name of the game")
    hide = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    start_time = models.DateTimeField(default=timezone.now, help_text="When match will be unlocked for betting.")
    title = models.CharField(max_length=255, help_text="title of the match. eg: Canada vs USA")

    def is_live(self):
        return not self.locked and self.start_time <= timezone.now() <= self.end_time

    def is_locked(self):
        return self.locked or self.end_time < timezone.now()

    def __str__(self):
        return f'{self.title}'

    class Meta:
        ordering = ['-end_time', '-start_time', 'game_name']


class QuestionOption(models.Model):
    option = models.CharField(max_length=255)
    rate = models.FloatField(default=1)


class BetQuestion(models.Model):
    end_time = models.DateTimeField(help_text="when this question will no longer accept bet", blank=True, null=True)
    hide = models.BooleanField(default=False, help_text="If the game is hidden")
    locked = models.BooleanField(default=False, help_text="Force lock question before end time")
    match = models.ForeignKey(Match, on_delete=models.CASCADE, help_text="Id of the match under which this is question")
    options = models.ManyToManyField(QuestionOption, help_text="Question options for user")
    paid = models.BooleanField(default=False, help_text="If all bet under this question is paid")
    question = models.CharField(max_length=1023, help_text="Question of bet")
    winner = models.ForeignKey(QuestionOption, on_delete=models.CASCADE, blank=True, null=True, related_name='gnn',
                               help_text="Winner option id")

    def is_locked(self):
        return bool(
            self.locked or self.match.is_locked() or self.winner or (self.end_time and self.end_time <= timezone.now()))

    def __str__(self):
        return f'{self.question}'

    class Meta:
        verbose_name_plural = 'Bet Options'
        ordering = ['-end_time']


class Bet(models.Model):
    amount = models.IntegerField(help_text='How much he/she bet')
    bet_question = models.ForeignKey(BetQuestion, on_delete=models.PROTECT, validators=[bet_scope_validator],
                                     help_text="For which question bet is done")
    choice = models.ForeignKey(QuestionOption, help_text="Choice for question", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, help_text="Time when bet is created")
    is_winner = models.BooleanField(default=None, blank=True, null=True, help_text="If this bet is winner")
    paid = models.BooleanField(default=False, help_text="If this bet is paid")
    win_rate = models.FloatField(default=1.00, blank=True, null=True, help_text="Multiplication with bet amount")
    user = models.ForeignKey(User, on_delete=models.CASCADE, help_text="User id who betting")
    user_balance = models.FloatField(default=0.0, help_text="User balance after bet")
    win_amount = models.FloatField(default=0, help_text='How much will get if wins')

    class Meta:
        ordering = ['bet_question', '-created_at']


class DepositWithdrawMethod(models.Model):
    method = models.CharField(max_length=255, help_text="Method name to be shown to users")
    number1 = models.CharField(max_length=32)
    number2 = models.CharField(max_length=32, null=True, blank=True)

    class Meta:
        verbose_name = 'Method'
        verbose_name_plural = 'Method List'


class Deposit(models.Model):
    amount = models.FloatField(help_text="how much money transacted in 2 point precession decimal number")
    balance = models.FloatField(default=0, blank=True, null=True, help_text="User possible balance after deposit")
    club = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, blank=True,
                             help_text="Club id which balance will be updated")
    created_at = models.DateTimeField(default=timezone.now, help_text="When deposit is made")
    deposit_source = models.CharField(max_length=50, choices=DEPOSIT_SOURCE,
                                      help_text="Options are, commission|bank|refer")
    method = models.CharField(max_length=50, choices=DEPOSIT_WITHDRAW_CHOICES,
                              help_text="method used to do transaction")
    site_account = models.CharField(max_length=255, blank=True, null=True,
                                    help_text="bank account number of the website")
    transaction_id = models.CharField(max_length=255, blank=True, null=True,
                                      help_text="Transaction id of user send money")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                             help_text="User id of transaction maker")
    user_account = models.CharField(max_length=255, blank=True, null=True,
                                    help_text="bank account number. Used for deposit and withdraw")
    status = models.BooleanField(default=None, null=True, blank=True,
                                 help_text="Status if admin had verified. After verification(for deposit), "
                                           "user account will be deposited")

    def __str__(self):
        return str(self.id)

    class Meta:
        ordering = ['-created_at']


class Transfer(models.Model):
    amount = models.FloatField(help_text="how much money transacted in 2 point precession decimal number")
    balance = models.FloatField(default=0, blank=True, null=True, help_text="User balance after transfer")
    club = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, blank=True,
                             help_text="Club Id from which money is going to be transferred")
    created_at = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True, null=True, help_text="Description of transfer")
    recipient = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recipients',
                                  help_text="User id to whom money transferred")
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, help_text="User id of transaction maker")
    status = models.BooleanField(default=None, blank=True, null=True,
                                 help_text="Status if admin had verified. After verification(for deposit), "
                                           "user account will be deposited")

    def __str__(self):
        return str(self.id)

    class Meta:
        ordering = ['-created_at']


class Withdraw(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, help_text="User id of transaction maker")
    method = models.CharField(max_length=50, choices=DEPOSIT_WITHDRAW_CHOICES,
                              help_text="method used to do transaction")
    amount = models.FloatField(help_text="how much money transacted in 2 point precession decimal number")
    user_account = models.CharField(max_length=255, blank=True, null=True,
                                    help_text="bank account number. Used for deposit and withdraw")
    site_account = models.CharField(max_length=255, blank=True, null=True,
                                    help_text="bank account number of the website")
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    user_balance = models.FloatField(default=0, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status = models.BooleanField(default=None, null=True, blank=True,
                                 help_text="Status if admin had verified. After verification(for deposit), "
                                           "user account will be deposited")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return str(self.id)

    class Meta:
        ordering = ['-created_at']
