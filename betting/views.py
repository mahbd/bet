from datetime import datetime, timedelta

from django.db.models import Sum, QuerySet
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.http import HttpResponse
from django.utils import timezone

from users.views import total_user_balance, total_club_balance, notify_user
from .models import TYPE_WITHDRAW, METHOD_TRANSFER, Bet, BetQuestion, METHOD_CLUB, Deposit, Withdraw, Transfer, Match, \
    config, SOURCE_REFER, SOURCE_COMMISSION


def create_deposit(user_id, amount, source, method=None, description=None, club=False):
    deposit = Deposit()
    if not club:
        deposit.user_id = user_id
    else:
        deposit.club_id = user_id
    deposit.method = method
    deposit.amount = amount
    deposit.description = description
    deposit.deposit_source = source
    deposit.save()
    return deposit


def pay_deposit(deposit: Deposit):
    if deposit.user:
        deposit.user.balance += deposit.amount
        deposit.user.save()
        deposit.balance = deposit.user.balance
        notify_user(deposit.user, f"Deposit request on {deposit.created_at} amount"
                                  f"{deposit.amount} confirmed")
    elif deposit.club:
        deposit.club.balance += deposit.amount
        deposit.club.save()
        deposit.balance = deposit.club.balance
    deposit.status = True
    deposit.save()


def cancel_deposit(deposit: Deposit):
    if deposit.status:
        # Change user Balance
        if deposit.user:
            deposit.user.balance -= deposit.amount
            deposit.user.save()
            # Change deposit status
            notify_user(deposit.user, f"Deposit request has been canceled placed on {deposit.created_at}."
                                      f"Contact admin if you think it was wrong. Transaction id: "
                                      f"{deposit.transaction_id} Amount: {deposit.amount} From "
                                      f"account: {deposit.user_account} To account {deposit.site_account} "
                                      f"Method: {deposit.method}")
        elif deposit.club:
            deposit.club.balance -= deposit.amount
            deposit.club.save()
            deposit.balance = deposit.club.balance
            # Change deposit status
            notify_user(deposit.club, f"Deposit request has been canceled placed on {deposit.created_at}."
                                      f"Contact admin if you think it was wrong. Transaction id: "
                                      f"{deposit.transaction_id} Amount: {deposit.amount} From "
                                      f"account: {deposit.user_account} To account {deposit.site_account} "
                                      f"Method: {deposit.method}", club=True)
    deposit.status = False
    deposit.save()


@receiver(post_delete, sender=Deposit)
def post_delete_deposit(instance: Deposit, *args, **kwargs):
    cancel_deposit(instance)


def cancel_withdraw(withdraw: Withdraw):
    """
    Increase user balance and make withdraw status false
    """
    withdraw.status = False
    withdraw.user.balance += withdraw.amount
    withdraw.user.save()
    withdraw.user_balance = withdraw.user.balance
    withdraw.save()
    notify_user(withdraw.user,
                f"Withdraw of {withdraw.amount}BDT via {withdraw.method} to number {withdraw.user_account} "
                f"placed on {withdraw.created_at} has been canceled and refunded")


def accept_withdraw(withdraw):
    """
    Mark status true if status is null
    Reduce balance and mark status true if status is False
    """

    if withdraw.status is None:
        withdraw.status = True
        withdraw.save()
    else:
        withdraw.status = True
        withdraw.user.balance -= withdraw.amount
        withdraw.user.save()
        withdraw.balance = withdraw.user.balance
        withdraw.save()
    notify_user(withdraw.user, f'Withdraw request create on {withdraw.created_at} is accepted.')


@receiver(post_save, sender=Withdraw)
def post_save_withdraw(instance: Withdraw, created: bool, *args, **kwargs):
    if created:
        # Reduce balance of user
        instance.user.balance -= instance.amount
        instance.user.save()
        # Update user balance during withdraw
        instance.user_balance = instance.user.balance
        instance.save()


@receiver(post_delete, sender=Withdraw)
def post_delete_withdraw(instance: Withdraw, *args, **kwargs):
    cancel_withdraw(instance)


def pay_transfer(transfer: Transfer):
    deposit = create_deposit(transfer.recipient_id, transfer.amount, METHOD_TRANSFER, METHOD_TRANSFER)
    pay_deposit(deposit)
    notify_user(transfer.recipient, f'You  received {transfer.amount} tk from user ##{transfer.sender.username}##, '
                                    f'with transfer id ##{transfer.id}##')
    transfer.status = True
    transfer.save()


def cancel_transfer(transfer: Transfer):
    if transfer.sender:
        notify_user(transfer.sender_id, f"Transfer of {transfer.amount}BDT to user {transfer.recipient.username} "
                                        f"placed on {transfer.created_at} has been canceled and refunded")
    notify_user(transfer.recipient_id, f"Transfer of {transfer.amount}BDT to you from {transfer.sender.username} "
                                       f"placed on {transfer.created_at} has been canceled")
    if transfer.status:
        transfer.recipient.balance -= transfer.amount
        transfer.recipient.save()
    if transfer.status is None:
        if transfer.sender:
            transfer.sender.balance += transfer.amount
            transfer.sender.save()
        if transfer.club:
            transfer.club.balance += transfer.amount
            transfer.club.save()
    transfer.status = False
    transfer.save()


@receiver(post_save, sender=Transfer)
def post_save_transfer(instance: Transfer, created: bool, *args, **kwargs):
    if created:
        notify_user(instance.recipient, f'You will receive {instance.amount} tk from user '
                                        f'##{instance.sender.username}## with transfer id '
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
    cancel_transfer(instance)


def pay_refer(bet: Bet) -> float:
    refer_commission = float(config.get_config_str('refer_commission')) / 100
    if bet.user.referred_by:
        commission = bet.amount * refer_commission
        bet.user.referred_by.earn_from_refer += commission
        bet.user.referred_by.save()
        deposit = create_deposit(bet.user.referred_by_id, commission, SOURCE_REFER, SOURCE_REFER)
        pay_deposit(deposit)
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
        pay_deposit(deposit)
        notify_user(bet.user.user_club, f"{bet.user.user_club.name} has "
                                        f"earned {commission} from "
                                        f"{bet.user.username}", club=True)
        bet.user.userclubinfo.total_commission += commission
        bet.user.userclubinfo.save()
        return commission
    return 0


@receiver(post_save, sender=Bet)
def post_process_bet(instance: Bet, created, *args, **kwargs):
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


def refund_bet(bet: Bet):
    # TODO: Verify logic
    change = bet.win_amount / bet.win_rate - bet.win_amount
    if not bet.paid or (bet.paid and not bet.is_winner):
        change = bet.win_amount / bet.win_rate
    bet.user.balance += change
    bet.user.save()
    notify_user(bet.user, f'Bet cancelled for match ##{bet.bet_question.match.title}## '
                          f'on ##{bet.bet_question.question}##. Balance '
                          f'refunded by {change} BDT')
    bet.paid = False
    bet.save()


@receiver(post_delete, sender=Bet)
def post_delete_bet(instance: Bet, *args, **kwargs):
    refund_bet(instance)


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
