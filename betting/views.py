from django.db.models.signals import post_save
from django.db.transaction import atomic
from django.dispatch import receiver

from .models import Transaction, TYPE_WITHDRAW, METHOD_TRANSFER, TYPE_DEPOSIT


def transfer_deposit(instance: Transaction):
    try:
        with atomic():
            instance.to.balance += instance.amount
            instance.to.save()
            transaction = Transaction()
            transaction.user = instance.to
            transaction.type = TYPE_DEPOSIT
            transaction.method = METHOD_TRANSFER
            transaction.amount = instance.amount
            transaction.pending = False
            transaction.save()
    except Exception as e:
        print(e)
        instance.delete()
        try:
            transaction.delete()
        except AttributeError:
            pass
        raise ValueError('Failed to process Transaction')  # TODO: Implement error logging


@receiver(post_save, sender=Transaction)
def post_process_transaction(instance: Transaction, created: bool, **kwargs):
    if created:
        if instance.type == TYPE_WITHDRAW:
            try:
                instance.user.balance -= instance.amount
                instance.user.save()
            except Exception as e:
                print(e)
                instance.delete()
                raise ValueError('Failed to process Transaction')  # TODO: Implement error logging
    else:
        if instance.type == TYPE_WITHDRAW and not instance.pending:
            if instance.method == METHOD_TRANSFER:
                transfer_deposit(instance)
