from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q, QuerySet
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.http import HttpResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from users.models import User
from users.views import total_user_balance, total_club_balance
from .models import TYPE_WITHDRAW, METHOD_TRANSFER, Bet, METHOD_BET, CHOICE_FIRST, \
    CHOICE_SECOND, BetScope, CHOICE_THIRD, METHOD_CLUB, Deposit, Withdraw, Transfer, Match, TYPE_DEPOSIT


def create_deposit(user_id: int, amount, method=None, description=None, verified=False):
    deposit = Deposit()
    deposit.user_id = user_id
    deposit.method = method
    deposit.amount = amount
    deposit.description = description
    deposit.verified = verified
    deposit.save()
    return deposit


@receiver(post_save, sender=Deposit)
def post_save_deposit(instance: Deposit, *args, **kwargs):
    if instance.verified and not instance.processed_internally and instance.method == METHOD_CLUB:
        instance.processed_internally = True
        instance.user.club.balance += instance.amount
        instance.user.club.save()

    elif instance.verified and not instance.processed_internally:
        instance.processed_internally = True
        instance.user.balance += instance.amount
        instance.user.save()
        instance.save()


@receiver(post_delete, sender=Deposit)
def post_delete_deposit(instance: Deposit, *args, **kwargs):
    if instance.verified and instance.method == METHOD_CLUB:
        instance.user.club.balance -= instance.amount
        instance.user.club.save()
    elif instance.verified:
        instance.user.balance -= instance.amount
        instance.user.save()
        # TODO: Implement to prevent from delete


@receiver(post_save, sender=Withdraw)
def post_save_withdraw(instance: Withdraw, created: bool, *args, **kwargs):
    if created:
        instance.user.balance -= instance.amount
        instance.user.full_clean()
        instance.user.save()
        instance.save()
    if instance.verified is False and instance.verified is not None and not instance.processed_internally:
        instance.processed_internally = True
        instance.user.balance += instance.amount
        instance.user.save()
        instance.save()
        instance.user.save()


@receiver(post_delete, sender=Withdraw)
def post_delete_withdraw(instance: Deposit, *args, **kwargs):
    if instance.verified:
        user = User.objects.get(pk=instance.user_id)
        user.balance += instance.amount
        user.full_clean()
        user.save()


@receiver(post_save, sender=Transfer)
def post_save_transfer(instance: Transfer, created: bool, *args, **kwargs):
    if created:
        instance.user.balance -= instance.amount
        instance.user.full_clean()
        instance.user.save()
        instance.save()
    if instance.verified and not instance.processed_internally:
        deposit = Deposit()
        deposit.user = instance.to
        deposit.method = METHOD_TRANSFER
        deposit.amount = instance.amount
        deposit.description = f'From **{instance.user_id}**, with transaction id ##{instance.id}##'
        deposit.verified = True
        deposit.save()

        instance.processed_internally = True
        instance.save()


@receiver(post_delete, sender=Transfer)
def post_delete_transfer(instance: Transfer, *args, **kwargs):
    if instance.verified:
        instance.to.balance -= instance.amount
        instance.to.full_clean()
        instance.to.save()
        # TODO: Implement to prevent delete
    instance.user.balance += instance.amount
    instance.user.save()


@receiver(post_save, sender=Bet)
def post_process_bet(instance: Bet, created, *args, **kwargs):
    if created:
        try:
            if instance.amount > instance.user.balance:
                raise ValueError("Does not have enough balance.")
            withdraw = Withdraw()
            withdraw.user = instance.user
            withdraw.method = METHOD_BET
            withdraw.amount = instance.amount
            withdraw.description = f'Balance used to bet on ##{instance.id}##'
            withdraw.verified = True
            withdraw.save()
        except Exception as e:
            print(e)
            instance.delete()


@receiver(post_delete, sender=Bet)
def post_delete_bet(instance: Bet, *args, **kwargs):
    create_deposit(user_id=int(instance.user_id), amount=instance.amount, method=METHOD_BET, verified=True,
                   description=f'Refund for match **{instance.bet_scope.match.title}** '
                               f'on ##{instance.bet_scope.question}##')


@receiver(post_save, sender=BetScope)
def post_process_game(instance: BetScope, *args, **kwargs):
    if not instance.processed_internally and instance.winner:
        with transaction.atomic():
            instance.processed_internally = True  # To avoid reprocessing the bet scope

            bet_winners = list(instance.bet_set.filter(choice=instance.winner))
            bet_losers = instance.bet_set.exclude(choice=instance.winner)
            if instance.winner == CHOICE_FIRST:
                ratio = instance.option_1_rate
            elif instance.winner == CHOICE_SECOND:
                ratio = instance.option_2_rate
            elif instance.winner == CHOICE_THIRD:
                ratio = instance.option_3_rate
            else:
                ratio = instance.option_4_rate

            for winner in bet_winners:
                win_amount = (winner.amount * ratio) * 0.975
                refer_amount = (winner.amount * ratio) * 0.005
                club_amount = (winner.amount * ratio) * 0.02
                create_deposit(winner.user_id, win_amount, method=METHOD_BET, verified=True,
                               description=f'User won on bet ##{winner.id}##')

                winner.status = 'Win %.2f' % win_amount
                winner.save()
                if winner.user.referred_by:
                    create_deposit(winner.user_id, refer_amount, METHOD_BET, verified=True,
                                   description=f'User won **{refer_amount}** by referring ##{winner.id}##')

                if winner.user.user_club:
                    create_deposit(winner.user_id, club_amount, METHOD_CLUB, verified=True,
                                   description=f'Club won **{club_amount}** from user ##{winner.id}##')
            bet_losers.update(status='Loss')
            instance.save()  # To avoid reprocessing the bet scope


def total_transaction_amount(t_type=None, method=None, date: datetime = None) -> float:
    if method == METHOD_TRANSFER and t_type == TYPE_WITHDRAW:
        all_transaction = Transfer.objects.filter(verified=True)
    elif t_type == TYPE_WITHDRAW:
        all_transaction = Withdraw.objects.filter(verified=True)
    else:
        all_transaction = Deposit.objects.filter(verified=True)
    if method and method != METHOD_TRANSFER:
        all_transaction.filter(method=method)
    if date:
        all_transaction = all_transaction.filter(created_at__gte=date)
    return float(all_transaction.aggregate(Sum('amount'))['amount__sum'])


def unverified_transaction_count(t_type=None, method=None, date: datetime = None) -> int:
    if method == METHOD_TRANSFER and t_type == TYPE_WITHDRAW:
        all_transaction = Transfer.objects.filter(verified__isnull=True)
    elif t_type == TYPE_WITHDRAW:
        all_transaction = Withdraw.objects.filter(verified__isnull=True)
    else:
        all_transaction = Deposit.objects.filter(verified__isnull=True)
    if date:
        all_transaction = all_transaction.filter(created_at__gte=date)
    return all_transaction.count()


def active_matches():
    return Match.objects.filter(locked=False, end_time__gte=timezone.now())


def active_bet_scopes():
    return BetScope.objects.filter(locked=False, match__locked=False, match__end_time__gte=timezone.now(),
                                   winner__isnull=True).exclude(end_time__lte=timezone.now())


def active_bet_scopes_count() -> int:
    return BetScope.objects.filter(locked=False, match__locked=False, match__end_time__gte=timezone.now(),
                                   winner__isnull=True).exclude(end_time__lte=timezone.now()).count()


def test_post(request):
    if request.method == 'POST':
        print(request.POST)
        return HttpResponse("Successfully made post request.")
    else:
        return HttpResponse("Failed to made post request.")


def get_file(request):
    link = request.META['HTTP_HOST']
    for key, value in request.META.items():
        print(value)
    return HttpResponse(link)


def sum_aggregate(queryset: QuerySet, field='amount'):
    return queryset.aggregate(Sum(field))[f'{field}__sum'] or 0


def generate_admin_dashboard_data():
    bet_or_club_q = Q(method=METHOD_BET) | Q(method=METHOD_CLUB)
    bet_or_club_or_transfer_q = bet_or_club_q | Q(method=METHOD_TRANSFER)
    bet_or_transfer = Q(method=METHOD_BET) | Q(method=METHOD_TRANSFER)
    total_bet_deposit = sum_aggregate(Deposit.objects.filter(bet_or_club_q))
    total_bet_withdraw = sum_aggregate(Withdraw.objects.filter(method=METHOD_BET))
    total_revenue = total_bet_withdraw - total_bet_deposit

    q = Deposit.objects.filter(bet_or_club_q, created_at__gte=timezone.now() - timedelta(days=30))
    month_bet_deposit = sum_aggregate(q)
    q = Withdraw.objects.filter(method=METHOD_BET, created_at__gte=timezone.now() - timedelta(days=30))
    month_bet_withdraw = sum_aggregate(q)
    last_month_revenue = month_bet_withdraw - month_bet_deposit

    total_deposit = sum_aggregate(Deposit.objects.exclude(bet_or_club_or_transfer_q))
    q = Deposit.objects.exclude(bet_or_club_or_transfer_q).filter(created_at__gte=timezone.now() - timedelta(days=30))
    last_month_deposit = sum_aggregate(q)

    total_withdraw = sum_aggregate(Withdraw.objects.exclude(bet_or_transfer))
    q = Withdraw.objects.exclude(bet_or_transfer).filter(created_at__gte=timezone.now() - timedelta(days=30))
    last_month_withdraw = sum_aggregate(q)

    data = {
        'total_user_balance': total_user_balance(),
        'total_club_balance': total_club_balance(),
        'total_bet_deposit': total_bet_deposit,
        'total_bet_withdraw': total_bet_withdraw,
        'total_revenue': total_revenue,
        'month_bet_deposit': month_bet_deposit,
        'month_bet_withdraw': month_bet_withdraw,
        'last_month_revenue': last_month_revenue,
        'total_deposit': total_deposit,
        'last_month_deposit': last_month_deposit,
        'total_withdraw': total_withdraw,
        'last_month_withdraw': last_month_withdraw
    }
    return data
