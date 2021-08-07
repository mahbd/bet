from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from users.models import User as MainUser

User: MainUser = get_user_model()

TYPE_DEPOSIT = 'D'
TYPE_WITHDRAW = 'W'
METHOD_BKASH = 'B'
METHOD_ROCKET = 'R'
METHOD_NAGAD = 'N'
METHOD_UPAY = 'U'
METHOD_TRANSFER = 'T'
CHOICE_FIRST = 'F'
CHOICE_SECOND = 'S'
CHOICE_DRAW = 'D'


def validate_receiver(sender: User, t_type, method, receiver: User):
    if t_type == 'W' and method == 'USER':
        if sender.user_club.admin != receiver and receiver.user_club.admin != sender:
            raise ValidationError("Transaction outside club is not allowed")
        if not receiver:
            raise ValidationError("Recipients is not selected")


class Transaction(models.Model):
    TYPE_CHOICES = (
        (TYPE_DEPOSIT, 'Deposit'),
        (TYPE_WITHDRAW, 'Withdrawal')
    )
    METHOD_CHOICES = (
        (METHOD_BKASH, 'BKash'),
        (METHOD_NAGAD, 'Nagad'),
        (METHOD_ROCKET, 'Rocket'),
        (METHOD_TRANSFER, 'Transfer')
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    type = models.CharField(max_length=1, choices=TYPE_CHOICES)
    method = models.CharField(max_length=255, choices=METHOD_CHOICES)
    to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recipients')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    account = models.CharField(max_length=255, blank=True, null=True)
    pending = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        validate_receiver(self.user, self.type, self.method, self.to)
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
    first = models.CharField(max_length=255)
    second = models.CharField(max_length=255)
    start = models.DateTimeField()
    end = models.DateTimeField()
    locked = models.BooleanField(default=False)

    def time_locked(self):
        return self.end <= timezone.now()


def validate_game(game: Game):
    if game.locked or game.time_locked():
        raise ValidationError('Bet is not allowed on this game!')


class Bet(models.Model):
    GAME_CHOICES = (
        (CHOICE_FIRST, 'First'),
        (CHOICE_DRAW, 'Draw'),
        (CHOICE_SECOND, 'Second'),
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    game = models.ForeignKey(Game, on_delete=models.PROTECT, validators=[validate_game])
    choice = models.CharField(max_length=2, choices=GAME_CHOICES)
    amount = models.IntegerField()
