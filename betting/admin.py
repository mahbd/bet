from django.contrib import admin
from django.utils import timezone

from .models import Transaction, Bet, Game, DepositWithdrawMethod


# noinspection PyMethodMayBeStatic
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'type', 'method', 'amount', 'verified']
    list_editable = ['verified']
    list_per_page = 50
    list_filter = ['verified', 'type', 'method', 'user']
    readonly_fields = ['id', 'user', 'type', 'method', 'to', 'transaction_id', 'account']
    fieldsets = (
        ('Verification Status', {
            'fields': ['verified']
        }),
        ('Type and Method', {
            'fields': ['type', 'method']
        }),
        ('Sensitive information', {
            'fields': ['transaction_id', 'amount', 'account']
        }),
        ('Other information', {
            'fields': ['user', 'to']
        })
    )

    def user(self, transaction: Transaction):
        return transaction.user.username


# noinspection PyMethodMayBeStatic
@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    search_fields = ['name', 'first', 'last']
    list_display = ['name', 'first', 'second', 'start', 'end', 'is_running']
    list_filter = ['name', 'first', 'second', 'start', 'end']
    fieldsets = (
        ('Status', {
            'fields': ['locked', 'winner']
        }),
        ('Basic Information', {
            'fields': ['name', 'first', 'second']
        }),
        ('Date Time information', {
            'fields': ['start', 'end']
        }),
        ('Win reward ratio', {
            'fields': ['first_ratio', 'second_ratio', 'draw_ratio']
        })
    )

    @admin.display(boolean=True)
    def is_running(self, game: Game):
        return game.end > timezone.now()


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = ['bet_by', 'game_id', 'choice', 'amount', 'created_at']
    list_filter = ['game', 'choice', 'user']
    autocomplete_fields = ['game']

    def bet_by(self, bet: Bet):
        return bet.user.username


@admin.register(DepositWithdrawMethod)
class DepositWithdrawMethodAdmin(admin.ModelAdmin):
    list_display = ['code', 'name']
