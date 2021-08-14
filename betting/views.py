from datetime import datetime

from django.db import transaction
from django.db.models import Sum
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

from users.models import User
from .models import TYPE_WITHDRAW, METHOD_TRANSFER, Bet, METHOD_BET, CHOICE_FIRST, \
    CHOICE_SECOND, BetScope, CHOICE_THIRD, METHOD_CLUB, Deposit, Withdraw, Transfer, Match


def create_deposit(user_id: User, amount, method=None, description=None, verified=False):
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


@receiver(post_delete, sender=Deposit)
def post_delete_withdraw(instance: Deposit, *args, **kwargs):
    instance.user.balance += instance.amount
    instance.user.save()


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
    if date:
        all_transaction = all_transaction.filter(created_at__gte=date)
    return float(all_transaction.aggregate(Sum('amount'))['amount__sum'])


def unverified_transaction_count(t_type=None, method=None, date: datetime = None) -> int:
    if method == METHOD_TRANSFER and t_type == TYPE_WITHDRAW:
        all_transaction = Transfer.objects.exclude(verified=True)
    elif t_type == TYPE_WITHDRAW:
        all_transaction = Withdraw.objects.exclude(verified=True)
    else:
        all_transaction = Deposit.objects.exclude(verified=True)
    if date:
        all_transaction = all_transaction.filter(created_at__gte=date)
    return all_transaction.count()


def active_matches():
    return Match.objects.filter(locked=False, end_time__gte=timezone.now())


def test_post(request):
    if request.method == 'POST':
        print(request.POST)
        return HttpResponse("Successfully made post request.")
    else:
        return HttpResponse("Failed to made post request.")


def get_file(request):
    return render(request, 'api/testPostRedirect.html')


def lock_bet_scope(request, bet_scope_id, rm=False):
    bet_scope = get_object_or_404(BetScope, pk=bet_scope_id)
    bet_scope.locked = True
    bet_scope.save()
    if rm:
        return redirect('admin:match')
    return redirect('admin:bet_option')
