from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from users.models import User as MainUser

User: MainUser = get_user_model()

TYPE_DEPOSIT = 'D'
TYPE_WITHDRAW = 'W'
METHOD_BKASH = 'B'
METHOD_ROCKET = 'R'
METHOD_NAGAD = 'N'
METHOD_TRANSFER = 'T'


def validate_to(t_type, method, to):
    if t_type == 'W' and method == 'USER':
        if not to:
            raise ValidationError("Recipients is not selected")


CHOICE_FIRST = 'F'
CHOICE_SECOND = 'S'


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
    phone = models.CharField(max_length=255, blank=True, null=True)
    pending = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        validate_to(self.type, self.method, self.to)
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


class Bet(models.Model):
    GAME_CHOICES = (
        (CHOICE_FIRST, 'First'),
        (CHOICE_SECOND, 'Second')
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    game = models.ForeignKey(Game, on_delete=models.PROTECT)
    choice = models.CharField(max_length=2, choices=GAME_CHOICES)
    amount = models.IntegerField()
