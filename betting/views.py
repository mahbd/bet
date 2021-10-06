from datetime import datetime, timedelta

from django.db.models import Sum, QuerySet
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.http import HttpResponse
from django.utils import timezone

from log.views import data_error_log
from users.views import total_user_balance, total_club_balance, notify_user
from .actions import accept_deposit, create_deposit, cancel_withdraw, cancel_deposit, cancel_transfer, refund_bet
from .choices import SOURCE_REFER, SOURCE_COMMISSION, TYPE_WITHDRAW, METHOD_TRANSFER, METHOD_CLUB
from .models import Bet, BetQuestion, Deposit, Withdraw, Transfer, Match, \
    ConfigModel, default_configs


def initialize_configuration(request):
    for key, value in default_configs.items():
        get_config_from_model(key)
    return HttpResponse('Ok')


def get_config_from_model(name: str, default=False) -> str:
    obj = ConfigModel.objects.filter(name=name)
    if obj:
        return str(obj[0].value)
    else:
        ConfigModel.objects.create(name=name, value=str(default or default_configs[name]))
        return str(default or default_configs[name])


def set_config_to_model(name: str, value: str) -> None:
    if ConfigModel.objects.filter(name=name).exists():
        ConfigModel.objects.filter(name=name).update(value=value)
    else:
        ConfigModel.objects.create(name=name, value=value)


@receiver(pre_delete, sender=Deposit)
def post_delete_deposit(instance: Deposit, *args, **kwargs):
    cancel_deposit(instance.id, delete=True)


@receiver(post_save, sender=Withdraw)
def post_save_withdraw(instance: Withdraw, created: bool, *args, **kwargs):
    if created:
        # Reduce balance of user
        instance.user.balance -= instance.amount
        instance.user.save()
        # Update user balance during withdraw
        instance.balance = instance.user.balance
        instance.save()


@receiver(post_delete, sender=Withdraw)
def post_delete_withdraw(instance: Withdraw, *args, **kwargs):
    cancel_withdraw(instance.id)


@receiver(post_save, sender=Transfer)
def post_save_transfer(instance: Transfer, created: bool, *args, **kwargs):
    if created:
        notify_user(instance.recipient, f'You will receive {instance.amount} tk from user/club '
                                        f'##{(instance.sender and instance.sender.username) or instance.club.name}## '
                                        f'with transfer id '
                                        f'##{instance.id}## as soon as admin confirms')
        if instance.sender:
            instance.sender.balance -= instance.amount
            instance.sender.save()
        elif instance.club:
            instance.club.balance -= instance.amount
            instance.club.save()
        if instance.sender is None and instance.club is None:
            instance.delete()


@receiver(pre_delete, sender=Transfer)
def post_delete_transfer(instance: Transfer, *args, **kwargs):
    cancel_transfer(instance.id)


def pay_refer(bet: Bet) -> float:
    refer_commission = float(get_config_from_model('refer_commission')) / 100
    if bet.user.referred_by:
        commission = bet.amount * refer_commission
        bet.user.referred_by.earn_from_refer += commission
        bet.user.referred_by.save()
        deposit = create_deposit(bet.user.referred_by_id, commission, SOURCE_REFER, SOURCE_REFER)
        accept_deposit(deposit.id)
        notify_user(bet.user.referred_by, f"You earned {commission} from user "
                                          f"{bet.user.username}. Keep referring and "
                                          f"earn {refer_commission * 100}% commission from each bet")
        return commission
    return 0


def pay_commission(bet: Bet) -> float:
    if bet.user.user_club:
        club = bet.user.user_club
        commission = bet.amount * club.club_commission / 100
        deposit = create_deposit(user_id=club.id, amount=commission,
                                 source=SOURCE_COMMISSION, method=SOURCE_COMMISSION, club=True)
        accept_deposit(deposit.id, message=f"{bet.user.user_club.name} has "
                                           f"earned {commission} from "
                                           f"{bet.user.username}")
        bet.user.userclubinfo.total_commission += commission
        bet.user.userclubinfo.save()
        return commission
    data_error_log(description=f'User {bet.user_id} does not have valid club')
    return 0


@receiver(post_save, sender=Bet)
def post_save_bet(instance: Bet, created, *args, **kwargs):
    if created:
        # Reduce balance on bet
        instance.user.balance -= instance.amount
        instance.user.save()
        # Pay refer and club
        refer_paid = pay_refer(instance)
        club_paid = pay_commission(instance)
        # Update bet instance information
        win_rate = instance.choice.rate
        instance.win_rate = win_rate
        instance.win_amount = (instance.amount - club_paid - refer_paid) * win_rate
        instance.user_balance = instance.user.balance
        instance.save()
        instance.user.userclubinfo.total_bet += instance.amount
        instance.user.userclubinfo.save()


@receiver(post_delete, sender=Bet)
def post_delete_bet(instance: Bet, *args, **kwargs):
    refund_bet(instance.id)


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


def active_bet_scopes():
    return BetQuestion.objects.filter(processed_internally=False)


def active_bet_scopes_count() -> int:
    return BetQuestion.objects.filter(processed_internally=False).count()


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
    total_bet_processed = sum_aggregate(Bet.objects.filter(paid=True))
    total_bet_made = sum_aggregate(Bet.objects.all())
    total_revenue = total_bet_processed - total_bet_win - total_bet_processed * 0.025

    q = Bet.objects.filter(paid=True).filter(created_at__gte=timezone.now() - timedelta(days=30))
    month_bet_win = sum_aggregate(q, 'winning')
    q = Bet.objects.filter(paid=True).filter(created_at__gte=timezone.now() - timedelta(days=30))
    month_bet = sum_aggregate(q)
    last_month_revenue = month_bet - month_bet_win - month_bet * 0.025

    total_deposit = sum_aggregate(Deposit.objects.exclude(method=METHOD_CLUB))
    q = Deposit.objects.exclude(method=METHOD_CLUB).filter(created_at__gte=timezone.now() - timedelta(days=30))
    last_month_deposit = sum_aggregate(q)

    total_withdraw = sum_aggregate(Withdraw.objects.all())
    q = Withdraw.objects.all().filter(created_at__gte=timezone.now() - timedelta(days=30))
    last_month_withdraw = sum_aggregate(q)

    data = {
        'total_user_balance': total_user_balance(),
        'total_club_balance': total_club_balance(),
        'total_bet': total_bet_made,
        'total_bet_payment': total_bet_win,
        'total_revenue': total_revenue,
        'last_30_day_bet': month_bet,
        'last_30_day_bet_payment': month_bet_win,
        'last_30_day_revenue': last_month_revenue,
        'total_deposit': total_deposit,
        'last_month_deposit': last_month_deposit,
        'total_withdraw': total_withdraw,
        'last_month_withdraw': last_month_withdraw
    }
    return data
