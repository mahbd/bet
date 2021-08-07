from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Transaction, TYPE_WITHDRAW, METHOD_TRANSFER, TYPE_DEPOSIT
from users.models import User


def transfer_deposit(instance: Transaction):
    try:
        transaction = Transaction()
        transaction.user = instance.to
        transaction.type = TYPE_DEPOSIT
        transaction.method = METHOD_TRANSFER
        transaction.amount = instance.amount
        transaction.verified = True
        transaction.save()
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
    if instance.type == TYPE_DEPOSIT and instance.verified:
        instance.user.balance += instance.amount
        instance.user.save()


@receiver(post_delete, sender=Transaction)
def post_delete_transaction(instance: Transaction, *args, **kwargs):
    if instance.type == TYPE_WITHDRAW:
        instance.user.balance += instance.amount
        instance.user.save()
