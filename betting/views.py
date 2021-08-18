from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Sum, QuerySet
from django.db.models.signals import post_save, post_delete, pre_delete, pre_save
from django.dispatch import receiver
from django.http import HttpResponse
from django.utils import timezone

from log.views import custom_log
from users.models import User
from users.views import total_user_balance, total_club_balance, notify_user
from .models import TYPE_WITHDRAW, METHOD_TRANSFER, Bet, BetScope, METHOD_CLUB, Deposit, Withdraw, Transfer, Match, \
    config, BET_CHOICES


def create_deposit(user_id: int, amount, method=None, description=None, verified=False):
    deposit = Deposit()
    deposit.user_id = user_id
    deposit.method = method
    deposit.amount = amount
    deposit.description = description
    deposit.verified = verified
    deposit.save()
    return deposit


def value_from_option(option: str, bet_scope: BetScope) -> str:
    print(option)
    if option == BET_CHOICES[0][0]:
        return bet_scope.option_1
    if option == BET_CHOICES[1][0]:
        return bet_scope.option_2
    if option == BET_CHOICES[2][0]:
        return bet_scope.option_3
    if option == BET_CHOICES[3][0]:
        return bet_scope.option_4
    return "Invalid option"


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
        instance.user_balance = instance.user.balance
        instance.save()


@receiver(post_delete, sender=Deposit)
def post_delete_deposit(instance: Deposit, *args, **kwargs):
    if instance.verified and instance.method == METHOD_CLUB:
        instance.user.club.balance -= instance.amount
        instance.user.club.save()
        notify_user(instance.user, f"Deposit request has been canceled placed on {instance.created_at}."
                                   f"Contact admin if you think it was wrong. Transaction id: {instance.transaction_id}"
                                   f" Amount: {instance.amount} From account: {instance.account} To account "
                                   f"{instance.superuser_account} Method: {instance.method}")
    elif instance.verified:
        try:
            instance.user.balance -= instance.amount
            instance.user.full_clean()
            instance.user.save()
        except Exception as e:
            custom_log(e, f"Failed to reduce balance of {instance.user.username} of {instance.amount} BDT due lack of "
                          f"balance.")


@receiver(post_save, sender=Withdraw)
def post_save_withdraw(instance: Withdraw, created: bool, *args, **kwargs):
    if created:
        instance.user.balance -= instance.amount
        instance.user.full_clean()
        instance.user.save()
        instance.user_balance = instance.user.balance
        instance.save()


@receiver(post_delete, sender=Withdraw)
def post_delete_withdraw(instance: Deposit, *args, **kwargs):
    notify_user(instance.user, f"Withdraw of {instance.amount}BDT via {instance.method} to number {instance.account} "
                               f"placed on {instance.created_at} has been canceled and refunded")
    if not instance.verified:
        user = User.objects.get(pk=instance.user_id)
        user.balance += instance.amount
        user.save()


@receiver(post_save, sender=Transfer)
def post_save_transfer(instance: Transfer, created: bool, *args, **kwargs):
    if created:
        if instance.amount > instance.user.balance - config.get_config('min_balance'):
            raise ValueError("Does not have enough balance.")
        instance.user.balance -= instance.amount
        instance.user.save()
        instance.user_balance = instance.user.balance
        instance.save()
    if instance.verified and not instance.processed_internally:
        deposit = Deposit()
        deposit.user = instance.to
        deposit.method = METHOD_TRANSFER
        deposit.amount = instance.amount
        deposit.description = f'From ##{instance.user.username}##, with transfer id ##{instance.id}##'
        deposit.verified = True
        deposit.save()

        instance.processed_internally = True
        instance.save()


@receiver(pre_delete, sender=Transfer)
def post_delete_transfer(instance: Transfer, *args, **kwargs):
    notify_user(instance.user, f"Transfer of {instance.amount}BDT to user {instance.to.username} placed on "
                               f"{instance.created_at} has been canceled and refunded")
    if instance.verified:
        try:
            instance.to.balance -= instance.amount
            instance.to.full_clean()
            instance.to.save()
        except Exception as e:
            custom_log(e, "Failed to reduce balance of user for transfer")
    instance.user.balance += instance.amount
    instance.user.save()


@receiver(post_save, sender=Bet)
def post_process_bet(instance: Bet, created, *args, **kwargs):
    if created:
        try:
            if instance.amount > instance.user.balance - config.get_config('min_balance'):
                raise ValueError("Does not have enough balance.")
            instance.user.balance -= instance.amount
            instance.user.save()
            if instance.choice == BET_CHOICES[0][0]:
                ratio = instance.bet_scope.option_1_rate
            elif instance.choice == BET_CHOICES[1][0]:
                ratio = instance.bet_scope.option_2_rate
            elif instance.choice == BET_CHOICES[2][0]:
                ratio = instance.bet_scope.option_3_rate
            else:
                ratio = instance.bet_scope.option_4_rate
            instance.return_rate = ratio
            instance.winning = instance.amount * ratio
            instance.save()
        except ValueError:
            instance.delete()
        except Exception as e:
            custom_log(e)
            instance.delete()


@receiver(pre_delete, sender=Bet)
def pre_delete_bet(instance: Bet, *args, **kwargs):
    if instance.winning - instance.amount > instance.user.balance:
        raise ValueError("User does not have enough balance.")
    change = instance.winning - instance.amount
    if not instance.paid:
        change = instance.amount
    instance.user.balance += change
    instance.user.save()
    notify_user(instance.user, f'Bet cancelled for match ##{instance.bet_scope.match.title}## '
                               f'on ##{instance.bet_scope.question}##. Balance '
                               f'refunded by {change} BDT')


@receiver(pre_save, sender=BetScope)
def post_process_game(instance: BetScope, *args, **kwargs):
    if not instance.processed_internally and instance.winner:
        with transaction.atomic():
            instance.processed_internally = True  # To avoid reprocessing the bet scope

            bet_winners = list(instance.bet_set.filter(choice=instance.winner))
            bet_losers = instance.bet_set.exclude(choice=instance.winner)
            club_commission = float(config.get_config_str('club_commission')) / 100
            refer_commission = float(config.get_config_str('refer_commission')) / 100

            for winner in bet_winners:
                winner.user.balance += winner.winning * (1 - club_commission - refer_commission)
                winner.user.save()
                winner.is_winner = True
                winner.answer = value_from_option(winner.choice, instance)
                winner.save()
                if winner.user.referred_by:
                    winner.user.referred_by.balance += winner.winning * refer_commission
                    winner.user.referred_by.earn_from_refer += winner.winning * refer_commission
                    notify_user(winner.user.referred_by, f"You earned {winner.winning * refer_commission} from user "
                                                         f"{winner.user.username}. Keep referring and "
                                                         f"earn {refer_commission}% commission from each bet")
                    winner.user.referred_by.save()

                if winner.user.user_club:
                    winner.user.user_club.balance += winner.winning * club_commission
                    winner.user.user_club.save()
                    notify_user(winner.user.user_club.admin, f"{winner.user.user_club.name} has "
                                                             f"earned {winner.winning * club_commission} from "
                                                             f"{winner.user.username}")
            for loser in bet_losers:
                loser.is_winner = False
                loser.winning = 0
                loser.answer = value_from_option(winner.choice, instance)
                loser.save()
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
    total_bet_win = sum_aggregate(Bet.objects.exclude(status='No result'), 'winning')
    total_bet = sum_aggregate(Bet.objects.exclude(status='No result'))
    total_revenue = total_bet - total_bet_win

    q = Bet.objects.exclude(status='No result').filter(created_at__gte=timezone.now() - timedelta(days=30))
    month_bet_win = sum_aggregate(q, 'winning')
    q = Bet.objects.exclude(status='No result').filter(created_at__gte=timezone.now() - timedelta(days=30))
    month_bet = sum_aggregate(q)
    last_month_revenue = month_bet - month_bet_win

    total_deposit = sum_aggregate(Deposit.objects.exclude(method=METHOD_CLUB))
    q = Deposit.objects.exclude(method=METHOD_CLUB).filter(created_at__gte=timezone.now() - timedelta(days=30))
    last_month_deposit = sum_aggregate(q)

    total_withdraw = sum_aggregate(Withdraw.objects.all())
    q = Withdraw.objects.all().filter(created_at__gte=timezone.now() - timedelta(days=30))
    last_month_withdraw = sum_aggregate(q)

    data = {
        'total_user_balance': total_user_balance(),
        'total_club_balance': total_club_balance(),
        'total_bet_deposit': total_bet_win,
        'total_bet_withdraw': total_bet,
        'total_revenue': total_revenue,
        'month_bet_deposit': month_bet_win,
        'month_bet_withdraw': month_bet,
        'last_month_revenue': last_month_revenue,
        'total_deposit': total_deposit,
        'last_month_deposit': last_month_deposit,
        'total_withdraw': total_withdraw,
        'last_month_withdraw': last_month_withdraw
    }
    return data
