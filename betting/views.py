from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Transaction, TYPE_WITHDRAW, METHOD_TRANSFER, TYPE_DEPOSIT, Bet, METHOD_BET, Game, CHOICE_FIRST, \
    CHOICE_SECOND
from users.models import User


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
        if instance.type == TYPE_WITHDRAW:
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
    if instance.type == TYPE_WITHDRAW:
        instance.user.balance += instance.amount
        instance.user.save()


@receiver(post_save, sender=Bet)
def post_process_bet(instance: Bet, created, *args, **kwargs):
    if created:
        try:
            if instance.amount > instance.user.balance:
                raise ValueError("Does not have enough balance.")
            create_transaction(instance.user, TYPE_WITHDRAW, METHOD_BET, instance.amount, verified=True)
        except:
            instance.delete()


@receiver(post_save, sender=Game)
def post_process_game(instance: Game, *args, **kwargs):
    if not instance.processed_internally and instance.winner:
        instance.processed_internally = True
        winners = list(instance.bet_set.filter(choice=instance.winner))
        losers = instance.bet_set.exclude(choice=instance.winner)
        if instance.winner == CHOICE_FIRST:
            ratio = instance.option_1_rate
        elif instance.winner == CHOICE_SECOND:
            ratio = instance.option_2_rate
        else:
            ratio = instance.draw_rate

        # Uncomment if auto complete rate
        # total_winners = sum([x.amount for x in winners])
        # total_losers = sum([x.amount for x in losers])
        # if not winners:
        #     ratio = 0
        # elif not losers:
        #     ratio = 1
        # else:
        #     ratio = (total_winners + total_losers) / total_winners

        for winner in winners:
            win_amount = (winner.amount * ratio) * 0.975
            refer_amount = (winner.amount * ratio) * 0.005
            create_transaction(winner.user, TYPE_DEPOSIT, f'{METHOD_BET}_{instance.id}', win_amount, verified=True)
            winner.status = 'Win %.2f' % ((winner.amount * ratio) * 0.98)
            winner.save()
            if winner.user.referred_by:
                create_transaction(winner.user.referred_by, TYPE_DEPOSIT, f'{METHOD_BET}_{instance.id}', refer_amount,
                                   verified=True)
        for loser in losers:
            loser.status = 'Loss'
            loser.save()
        instance.save()
