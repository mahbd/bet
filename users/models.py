from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models


class Club(models.Model):
    admin = models.OneToOneField('User', on_delete=models.SET_NULL, null=True, help_text="Club admin id")
    name = models.CharField(max_length=255, help_text="Name of the club")

    def __str__(self):
        return self.name


class User(AbstractUser):
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                  validators=[MinValueValidator(0)],
                                  help_text='Users current balance. ')
    user_club = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, help_text='Users current club.')
    email = models.EmailField('Email address', unique=True)
    phone = models.CharField('Phone number', max_length=18, unique=True)
    game_editor = models.BooleanField(default=False, help_text='Decides if user can create add and update live match.')
    referred_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='refer_set',
                                    help_text='Who referred this user')

    def is_club_admin(self):
        try:
            bool(self.club)
            response = True
        except Club.DoesNotExist:
            response = False
        return response

    def __str__(self):
        return self.username
