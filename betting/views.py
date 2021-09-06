from datetime import datetime, timedelta

from django.db.models import Sum, QuerySet
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.http import HttpResponse
from django.utils import timezone

from log.views import custom_log
from users.models import User
from users.views import total_user_balance, total_club_balance, notify_user
from .models import TYPE_WITHDRAW, METHOD_TRANSFER, Bet, BetScope, METHOD_CLUB, Deposit, Withdraw, Transfer, Match, \
    config, BET_CHOICES, ClubTransfer, Commission, COMMISSION_REFER, COMMISSION_CLUB


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
    if option == BET_CHOICES[0][0]:
        return bet_scope.option_1
    if option == BET_CHOICES[1][0]:
        return bet_scope.option_2
    if option == BET_CHOICES[2][0]:
        return bet_scope.option_3
    if option == BET_CHOICES[3][0]:
        return bet_scope.option_4
    return "Invalid option"


def pay_deposit(deposit: Deposit):
    deposit.processed_internally = True
    deposit.user_balance = deposit.user.balance + deposit.amount
    deposit.user.balance += deposit.amount
    deposit.user.save()
    deposit.save()


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


@receiver(post_delete, sender=ClubTransfer)
def post_delete_transfer(instance: ClubTransfer, *args, **kwargs):
    notify_user(instance.club.admin, f"Transfer of {instance.amount}BDT to user {instance.to.username} placed on "
                                     f"{instance.created_at} has been canceled and refunded")
    if instance.verified:
        try:
            instance.to.balance -= instance.amount
            instance.to.full_clean()
            instance.to.save()
            instance.club.balance += instance.amount
            instance.club.save()
        except Exception as e:
            custom_log(e, "Failed to reduce balance of user for transfer")
    else:
        instance.club.balance += instance.amount
        instance.club.save()


@receiver(post_save, sender=ClubTransfer)
def post_save_transfer(instance: ClubTransfer, created: bool, *args, **kwargs):
    if created:
        if instance.amount > instance.club.balance - config.get_config('min_balance'):
            raise ValueError("Club does not have enough balance.")
        instance.club.balance -= instance.amount
        instance.club.save()
        instance.club_balance = instance.club.balance
        instance.save()
    if instance.verified and not instance.processed_internally:
        instance.to.balance += instance.amount
        instance.to.save()
        notify_user(instance.to, f'Received tk {instance.amount} from ##{instance.club.username}##, with transfer '
                                 f'id ##{instance.id}##')
        instance.processed_internally = True
        instance.save()


def get_rate(choice, bet_scope: BetScope):
    if choice == BET_CHOICES[0][0]:
        ratio = bet_scope.option_1_rate
    elif choice == BET_CHOICES[1][0]:
        ratio = bet_scope.option_2_rate
    elif choice == BET_CHOICES[2][0]:
        ratio = bet_scope.option_3_rate
    else:
        ratio = bet_scope.option_4_rate
    return ratio


def pay_refer(bet: Bet) -> float:
    refer_commission = float(config.get_config_str('refer_commission')) / 100
    if bet.user.referred_by:
        commission = bet.amount * refer_commission
        bet.user.referred_by.balance += commission
        bet.user.referred_by.earn_from_refer += commission
        notify_user(bet.user.referred_by, f"You earned {commission} from user "
                                          f"{bet.user.username}. Keep referring and "
                                          f"earn {refer_commission * 100}% commission from each bet")
        bet.user.referred_by.save()
        Commission.objects.create(bet=bet, amount=commission,
                                  type=COMMISSION_REFER, balance=bet.user.referred_by.balance)
        return commission
    return 0


def pay_club(bet: Bet) -> float:
    if bet.user.user_club:
        commission = bet.amount * bet.user.user_club.club_commission / 100
        bet.user.user_club.balance += commission
        bet.user.user_club.save()
        notify_user(bet.user.user_club.admin, f"{bet.user.user_club.name} has "
                                              f"earned {commission} from "
                                              f"{bet.user.username}")
        Commission.objects.create(bet=bet, amount=commission,
                                  club=bet.user.user_club,
                                  type=COMMISSION_CLUB, balance=bet.user.user_club.balance)
        bet.user.userclubinfo.total_commission += commission
        bet.user.userclubinfo.save()
        return commission
    return 0


@receiver(post_save, sender=Bet)
def post_process_bet(instance: Bet, created, *args, **kwargs):
    if created:
        try:
            if instance.amount > instance.user.balance - config.get_config('min_balance'):
                raise ValueError("Does not have enough balance.")
            instance.user.balance -= instance.amount
            instance.user.save()
            refer_paid = pay_refer(instance)
            club_paid = pay_club(instance)
            ratio = get_rate(instance.choice, instance.bet_scope)

            instance.return_rate = ratio
            instance.winning = (instance.amount - club_paid - refer_paid) * ratio
            instance.balance = instance.user.balance
            instance.save()
        except ValueError:
            instance.delete()
        except Exception as e:
            custom_log(e)
            instance.delete()


@receiver(post_delete, sender=Bet)
def post_delete_bet(instance: Bet, *args, **kwargs):
    try:
        change = -instance.winning * (instance.return_rate - 1.00)
        if not instance.paid or (instance.paid and not instance.is_winner):
            change = instance.winning / instance.return_rate
        instance.user.balance += change
        instance.user.save()
        notify_user(instance.user, f'Bet cancelled for match ##{instance.bet_scope.match.title}## '
                                   f'on ##{instance.bet_scope.question}##. Balance '
                                   f'refunded by {change} BDT')
    except Exception as e:
        custom_log(e,f'Error post delete bet of user {instance.user.username} bet id {instance.id} amount:'
                     f' {instance.amount} date: {instance.created_at}')


def sum_aggregate(queryset: QuerySet, field='amount'):
    return queryset.aggregate(Sum(field))[f'{field}__sum'] or 0


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
    return float(sum_aggregate(all_transaction))


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
    return BetScope.objects.filter(processed_internally=False)


def active_bet_scopes_count() -> int:
    return BetScope.objects.filter(processed_internally=False).count()


def test_post(request):
    if request.method == 'POST':
        print(request.POST)
        return HttpResponse("Successfully made post request.")
    else:
        return HttpResponse("Failed to made post request.")


def get_last_bet(user=None):
    if user:
        return Bet.objects.order_by('created_at').filter(user=user).last()
    return Bet.objects.order_by('created_at').last()


def total_bet(user=None):
    if user:
        return sum_aggregate(Bet.objects.order_by('created_at').filter(user=user))
    return sum_aggregate(Bet.objects.order_by('created_at'))


def get_file(request):
    link = request.META['HTTP_HOST']
    for key, value in request.META.items():
        print(value)
    return HttpResponse(link)


def generate_admin_dashboard_data():
    total_bet_win = sum_aggregate(Bet.objects.filter(paid=True), 'winning')
    total_bet = sum_aggregate(Bet.objects.filter(paid=True))
    total_revenue = total_bet - total_bet_win

    q = Bet.objects.filter(paid=True).filter(created_at__gte=timezone.now() - timedelta(days=30))
    month_bet_win = sum_aggregate(q, 'winning')
    q = Bet.objects.filter(paid=True).filter(created_at__gte=timezone.now() - timedelta(days=30))
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
