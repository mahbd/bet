from django.contrib import admin

from .models import Transaction, Bet


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    pass


@admin.register(Bet)
class Bet(admin.ModelAdmin):
    pass
