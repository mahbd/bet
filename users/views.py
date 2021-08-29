from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User, Club, Notification, UserClubInfo


def sum_aggregate(queryset, field='amount'):
    return queryset.aggregate(Sum(field))[f'{field}__sum'] or 0


def total_user_balance() -> float:
    all_user = User.objects.all()
    return float(all_user.aggregate(Sum('balance'))['balance__sum'])


def total_club_balance() -> float:
    return sum_aggregate(Club.objects.all(), 'balance')


def notify_user(user, message):
    Notification.objects.create(user=user, message=message)


@receiver(post_save, sender=User)
def create_user_club_info(instance: User, *args, **kwargs):
    if not UserClubInfo.objects.filter(user_id=instance.id, club_id=instance.user_club_id):
        UserClubInfo.objects.filter(user_id=instance.id).delete()
        UserClubInfo.objects.create(user_id=instance.id, club_id=instance.user_club_id)
