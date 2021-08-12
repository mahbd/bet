from django.db.models import Sum

from .models import User, Club


def total_user_balance() -> float:
    all_user = User.objects.all()
    return float(all_user.aggregate(Sum('balance'))['balance__sum'])


def total_club_balance() -> float:
    all_club = Club.objects.all()
    return float(all_club.aggregate(Sum('balance'))['balance__sum'])
