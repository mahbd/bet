from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Transaction, TYPE_WITHDRAW, METHOD_TRANSFER, TYPE_DEPOSIT


@receiver(post_save, sender=Transaction)
def post_process_transaction(instance: Transaction, created: bool, **kwargs):
    Transaction.objects.raw('LOCK TABLES `main_transaction` WRITE;')
    if created and instance.type == TYPE_WITHDRAW and instance.method == METHOD_TRANSFER:
        try:
            transaction = Transaction()
            transaction.user = instance.user
            transaction.type = TYPE_DEPOSIT
            transaction.method = METHOD_TRANSFER
            transaction.amount = instance.amount
            transaction.save()
        except Exception as e:
            print(e)
            instance.delete()
            raise ValueError('Failed to process Transaction')  # TODO: Implement error logging
    Transaction.objects.raw('UNLOCK TABLES;')
