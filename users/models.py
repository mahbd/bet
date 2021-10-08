from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string


def login_key():
    return get_random_string(10)


class Club(models.Model):
    admin = models.OneToOneField('User', on_delete=models.SET_NULL,
                                 null=True, blank=True, help_text="Club admin id")
    balance = models.FloatField(default=0)
    club_commission = models.FloatField(default=2)
    name = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    username = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ('-balance', )

    def __str__(self):
        return self.name


class User(AbstractUser):
    balance = models.FloatField(default=0)
    earn_from_refer = models.FloatField(default=0)
    email = models.EmailField('Email address', unique=True)
    game_editor = models.BooleanField(default=False)
    login_key = models.CharField(max_length=255, default=login_key)
    phone = models.CharField('Phone number', max_length=18, unique=True)
    referred_by = models.ForeignKey('User', on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='refer_set')
    user_club = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True)

    def is_club_admin(self):
        try:
            bool(self.club)
            response = True
        except Club.DoesNotExist:
            response = False
        return response

    def __str__(self):
        return self.username


class UserClubInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    total_bet = models.FloatField(default=0)
    total_commission = models.FloatField(default=0)


class Notification(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    message = models.TextField()
    viewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
