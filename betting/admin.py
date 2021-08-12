from bet import admin
from django.db.models import F
from django.shortcuts import render
from django.urls import path
from django.utils.html import format_html

from .models import Transaction, Bet, BetScope, Match, DepositWithdrawMethod


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'type', 'method', 'amount', 'verified']
    autocomplete_fields = ['user', 'to']
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
            'fields': ['transaction_id', 'amount', 'account', 'superuser_account']
        }),
        ('Other information', {
            'fields': ['user', 'to']
        })
    )

    # noinspection PyMethodMayBeStatic
    def user(self, transaction: Transaction):
        return transaction.user.username

    def deposit(self, request):
        request.current_app = self.admin_site.name
        context = dict(
            self.admin_site.each_context(request),
        )

        return render(request, 'admin/deposit.html', context)

    def withdraw(self, request):
        request.current_app = self.admin_site.name
        context = dict(
            self.admin_site.each_context(request),
        )

        return render(request, 'admin/withdraw.html', context)

    def transfer(self, request):
        request.current_app = self.admin_site.name
        context = dict(
            self.admin_site.each_context(request),
        )

        return render(request, 'admin/transfer.html', context)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('deposit/', self.deposit, name='deposit'),
            path('withdraw/', self.withdraw, name='withdraw'),
            path('transfer/', self.transfer, name='transfer'),
        ]
        return my_urls + urls


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    search_fields = ['game_name', 'title', 'start_time']
    list_display = ['game_name', 'title', 'start_time', 'end_time', 'bet_scopes']
    list_filter = ['game_name', 'start_time', 'end_time']
    fieldsets = (
        ('Basic Information', {
            'fields': ['game_name', 'title']
        }),
        ('Date Time information', {
            'fields': ['start_time', 'end_time']
        })
    )

    # noinspection PyMethodMayBeStatic
    def bet_scopes(self, match: Match):
        return format_html('<a href="/admin/betting/betscope/?match__id__exact={}">{} scope(s)</a>', match.id,
                           match.betscope_set.count())


@admin.register(BetScope)
class BetScopeAdmin(admin.ModelAdmin):
    list_display = ['id', 'match_link', 'question', 'is_running']
    search_fields = ['match_title', 'start_time', 'question']
    autocomplete_fields = ['match']
    list_filter = ['match']
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

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            match_title=F('match__title')
        )

    def match_link(self, bet_scope):
        return format_html('<a href=/admin/betting/match/{}/change/>{}</a>', bet_scope.match_id, bet_scope.match_title)

    # noinspection PyMethodMayBeStatic
    def match_title(self,  bet_scope: BetScope):
        return bet_scope.match.title

    @admin.display(boolean=True)
    def is_running(self, bet_scope: BetScope):
        return not bet_scope.is_locked()

    def bet_option(self, request):
        request.current_app = self.admin_site.name
        context = dict(
            self.admin_site.each_context(request),
        )

        return render(request, 'admin/bet_option.html', context)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('bet_option/', self.bet_option, name='bet_option'),
        ]
        return my_urls + urls


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = ['id', 'bet_by', 'bet_scope_link', 'choice', 'amount', 'status', 'created_at']
    readonly_fields = ['status', 'created_at']
    list_filter = ['choice', 'bet_scope', 'user']
    autocomplete_fields = ['bet_scope', 'user']

    # noinspection PyMethodMayBeStatic
    def bet_by(self, bet: Bet):
        return format_html('<a href=/admin/users/user/{}/change/>{}</a>', bet.user.id, bet.user.username)

    # noinspection PyMethodMayBeStatic
    def bet_scope_link(self, bet: Bet):
        return format_html('<a href=/admin/betting/betscope/{}/change/>{}</a>', bet.bet_scope_id, bet.bet_scope)


@admin.register(DepositWithdrawMethod)
class DepositWithdrawMethodAdmin(admin.ModelAdmin):
    list_display = ['code', 'name']
