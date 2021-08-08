from django.contrib import admin
from django.utils import timezone

from .models import Transaction, Bet, Game, DepositWithdrawMethod


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

    # noinspection PyMethodMayBeStatic
    def user(self, transaction: Transaction):
        return transaction.user.username


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    search_fields = ['name', 'option_1', 'last']
    list_display = ['name', 'option_1', 'option_2', 'start_time', 'end_time', 'is_running']
    list_filter = ['name', 'option_1', 'option_2', 'start_time', 'end_time']
    fieldsets = (
        ('Status', {
            'fields': ['locked', 'winner']
        }),
        ('Basic Information', {
            'fields': ['name', 'option_1', 'option_2']
        }),
        ('Date Time information', {
            'fields': ['start_time', 'end_time']
        }),
        ('Win reward ratio', {
            'fields': ['option_1_rate', 'option_2_rate', 'draw_rate']
        })
    )

    @admin.display(boolean=True)
    def is_running(self, game: Game):
        return game.end_time > timezone.now()


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = ['bet_by', 'game_id', 'choice', 'amount', 'created_at']
    list_filter = ['choice', 'game', 'user']
    autocomplete_fields = ['game']

    # noinspection PyMethodMayBeStatic
    def bet_by(self, bet: Bet):
        return bet.user.username


@admin.register(DepositWithdrawMethod)
class DepositWithdrawMethodAdmin(admin.ModelAdmin):
    list_display = ['code', 'name']
