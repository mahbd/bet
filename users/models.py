from django.contrib.auth.models import AbstractUser
from django.db import models


class Club(models.Model):
    admin = models.OneToOneField('User', on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=255)


class User(AbstractUser):
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    user_club = models.ForeignKey(Club, on_delete=models.SET_NULL, null=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=18, unique=True)

    def __str__(self):
        return self.username
