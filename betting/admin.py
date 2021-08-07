from django.contrib import admin
from django.utils import timezone

from .models import Transaction, Bet, Game


# noinspection PyMethodMayBeStatic
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'type', 'method', 'amount', 'verified']
    list_filter = ['verified', 'type', 'method', 'user']

    def user(self, transaction: Transaction):
        return transaction.user.username


# noinspection PyMethodMayBeStatic
@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['name', 'first', 'second', 'start', 'end', 'is_running']
    list_filter = ['name', 'first', 'second', 'start', 'end']

    @admin.display(boolean=True)
    def is_running(self, game: Game):
        return game.end > timezone.now()


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = ['bet_by', 'game_id', 'choice', 'amount', 'created_at']
    list_filter = ['game', 'choice', 'user']

    def bet_by(self, bet: Bet):
        return bet.user.username
