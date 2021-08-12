from decimal import Decimal, getcontext

from django.db.models import F
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from users.models import User, Club
from .models import Transaction, TYPE_WITHDRAW, METHOD_TRANSFER, TYPE_DEPOSIT, Bet, METHOD_BET, CHOICE_FIRST, \
    CHOICE_SECOND, BetScope, CHOICE_THIRD, METHOD_BET_ODD, METHOD_BET_EVEN, METHOD_CLUB


def create_transaction(user, t_type, method, amount, verified=False):
    transaction = Transaction()
    transaction.user = user
    transaction.type = t_type
    transaction.method = method
    transaction.amount = amount
    transaction.verified = verified
    transaction.save()
    return transaction


def transfer_deposit(instance: Transaction):
    try:
        create_transaction(instance.to, TYPE_DEPOSIT, METHOD_TRANSFER, instance.amount, verified=True)
    except Exception as e:
        print(e)
        instance.delete()


@receiver(post_save, sender=Transaction)
def post_process_transaction(instance: Transaction, created: bool, **kwargs):
    if created:
        if instance.type == TYPE_WITHDRAW and instance.method == METHOD_CLUB:
            try:
                club = Club.objects.get(pk=instance.user.club.id)
                club.balance -= instance.amount
                club.full_clean()
                club.save()
            except Exception as e:
                print(e)
                instance.delete()
                raise ValueError('Failed to process Transaction')  # TODO: Implement error logging
        elif instance.type == TYPE_WITHDRAW:
            try:
                user = User.objects.get(pk=instance.user.id)
                user.balance -= instance.amount
                user.full_clean()
                user.save()
            except Exception as e:
                print(e)
                instance.delete()
                raise ValueError('Failed to process Transaction')  # TODO: Implement error logging
    if instance.type == TYPE_WITHDRAW and instance.verified:
        if instance.method == METHOD_TRANSFER:
            transfer_deposit(instance)
    if instance.type == TYPE_DEPOSIT and instance.verified and not instance.processed_internally:
        instance.user.balance += instance.amount
        instance.processed_internally = True
        instance.user.save()


@receiver(post_delete, sender=Transaction)
def post_delete_transaction(instance: Transaction, *args, **kwargs):
    if instance.type == TYPE_WITHDRAW and instance.method == METHOD_CLUB:
        instance.user.club.balance += instance.amount
        instance.user.club.save()
    elif instance.type == TYPE_WITHDRAW:
        instance.user.balance += instance.amount
        instance.user.save()


@receiver(post_save, sender=Bet)
def post_process_bet(instance: Bet, created, *args, **kwargs):
    if created:
        try:
            if instance.amount > instance.user.balance:
                raise ValueError("Does not have enough balance.")
            create_transaction(instance.user, TYPE_WITHDRAW, METHOD_BET, instance.amount, verified=True)
        except Exception as e:
            print(e)
            instance.delete()


@receiver(post_save, sender=BetScope)
def post_process_game(instance: BetScope, *args, **kwargs):
    if not instance.processed_internally and instance.winner:
        getcontext().prec = 2
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

        # Uncomment if auto complete rate
        # total_winners = sum([x.amount for x in winners])
        # total_losers = sum([x.amount for x in losers])
        # if not winners:
        #     ratio = 0
        # elif not losers:
        #     ratio = 1
        # else:
        #     ratio = (total_winners + total_losers) / total_winners

        for winner in bet_winners:
            win_amount = (winner.amount * ratio) * Decimal(0.975)
            refer_amount = (winner.amount * ratio) * Decimal(0.005)
            create_transaction(winner.user, TYPE_DEPOSIT, f'{METHOD_BET_ODD if instance.id & 1 else METHOD_BET_EVEN}',
                               win_amount, verified=True)
            winner.status = 'Win %.2f' % win_amount
            winner.save()
            if winner.user.referred_by:
                create_transaction(winner.user.referred_by, TYPE_DEPOSIT, f'{METHOD_BET}_{instance.id}', refer_amount,
                                   verified=True)
            if winner.user.user_club:
                club = Club.objects.get(id=winner.user.user_club_id)
                club.objects.update(balance=F('balance') + (winner.amount * ratio) * Decimal(0.02))
        bet_losers.update(status='Loss')
        instance.save()  # To avoid reprocessing the bet scope
