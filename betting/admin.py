from django.contrib.admin import StackedInline
from django.db.models import F
from django.shortcuts import render
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html

from bet import admin
from .models import Bet, BetScope, Match, DepositWithdrawMethod, Deposit, Withdraw, Transfer


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
    def match_title(self, bet_scope: BetScope):
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

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        form.base_fields['match'].initial = request.GET.get('match_id')
        return form


class BetScopeInline(StackedInline):
    model = BetScope
    extra = 0


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    search_fields = ['game_name', 'title', 'start_time']
    list_display = ['game_name', 'title', 'start_time', 'end_time', 'bet_scopes', 'add']
    list_filter = ['game_name', 'start_time', 'end_time']
    inlines = [BetScopeInline]
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

    def match(self, request):
        request.current_app = self.admin_site.name
        context = dict(
            self.admin_site.each_context(request),
            match_list=Match.objects.filter(end_time__gte=timezone.now())
        )

        return render(request, 'admin/match.html', context)

    def add(self, match):
        return format_html('<a href="/admin/betting/betscope/add/?match_id={}">add</a>', match.id)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('match/', self.match, name='match'),
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


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'method', 'verified')
    list_filter = ('method', )
    autocomplete_fields = ('user',)


@admin.register(Withdraw)
class WithdrawAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'method', 'verified')
    list_filter = ('method',)
    autocomplete_fields = ('user', )


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('user', 'to', 'amount', )
    autocomplete_fields = ('user', 'to', )
