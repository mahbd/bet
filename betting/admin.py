from django.contrib import admin

from .models import Transaction, Bet, BetScope, Match, DepositWithdrawMethod


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'type', 'method', 'amount', 'verified']
    list_editable = ['verified']
    list_per_page = 50
    list_filter = ['verified', 'type', 'method', 'created_at', 'user']
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


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    search_fields = ['game_name', 'title', 'start_time']
    list_display = ['game_name', 'title', 'start_time', 'end_time', ]
    list_filter = ['game_name', 'start_time', 'end_time']
    fieldsets = (
        ('Basic Information', {
            'fields': ['game_name', 'title']
        }),
        ('Date Time information', {
            'fields': ['start_time', 'end_time']
        })
    )


@admin.register(BetScope)
class BetScopeAdmin(admin.ModelAdmin):
    list_display = ['match_title', 'question']
    search_fields = ['match_title', 'question']
    autocomplete_fields = ['match']
    fieldsets = (
        ('Basic Information', {
            'fields': ['match', 'question']
        }),
        ('Change carefully', {
            'classes': ('collapse',),
            'fields': ['locked', 'winner']
        }),
        ('Bet Options', {
            'fields': ['option_1', 'option_1_rate', 'option_2', 'option_2_rate',
                       'option_3', 'option_3_rate', 'option_4', 'option_4_rate']
        }),
        ('Date Time information', {
            'fields': ['start_time', 'end_time']
        })
    )

    # noinspection PyMethodMayBeStatic
    def match_title(self, bet_scope: BetScope):
        return bet_scope.match.title


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = ['bet_by', 'bet_scope', 'choice', 'amount', 'created_at']
    list_filter = ['choice', 'bet_scope', 'user']
    autocomplete_fields = ['bet_scope']

    # noinspection PyMethodMayBeStatic
    def bet_by(self, bet: Bet):
        return bet.user.username


@admin.register(DepositWithdrawMethod)
class DepositWithdrawMethodAdmin(admin.ModelAdmin):
    list_display = ['code', 'name']
