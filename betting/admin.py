from django.contrib import admin

from .models import Transaction, Bet


# noinspection PyMethodMayBeStatic
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'type', 'method', 'amount', 'verified']
    list_filter = ['verified', 'type', 'method', 'user']

    def user(self, transaction: Transaction):
        return transaction.user.username


@admin.register(Bet)
class Bet(admin.ModelAdmin):
    pass
