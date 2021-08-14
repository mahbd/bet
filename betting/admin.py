from django.contrib.admin import StackedInline
from django.db.models import F, Sum
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html

from bet import admin
from .models import Bet, BetScope, Match, DepositWithdrawMethod, Deposit, Withdraw, Transfer, Announcement, \
    CHOICE_FIRST, CHOICE_SECOND, CHOICE_THIRD, CHOICE_FOURTH
from .views import active_bet_scopes


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
            'classes': ('collapse',),
            'fields': ['option_1', 'option_1_rate', 'option_2', 'option_2_rate',
                       'option_3', 'option_3_rate', 'option_4', 'option_4_rate']
        }),
        ('Date Time information', {
            'classes': ('collapse',),
            'fields': ['start_time', 'end_time']
        })
    )

    def get_queryset(self, request):
        return BetScope.objects.select_related('match').all().annotate(
            match_title=F('match__title')
        )

    # noinspection PyMethodMayBeStatic
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
            live_bet_scope_list=active_bet_scopes().select_related('match'),
        )

        return render(request, 'admin/bet_option.html', context)

    def bet_scope_detail(self, request, bet_scope_id):
        request.current_app = self.admin_site.name
        try:
            bet_scope = BetScope.objects.get(pk=bet_scope_id)
        except BetScope.DoesNotExist:
            raise Http404
        option1_bet = bet_scope.bet_set.filter(choice=CHOICE_FIRST).aggregate(Sum('amount'))['amount__sum'] or 0
        option2_bet = bet_scope.bet_set.filter(choice=CHOICE_SECOND).aggregate(Sum('amount'))['amount__sum'] or 0
        option3_bet = bet_scope.bet_set.filter(choice=CHOICE_THIRD).aggregate(Sum('amount'))['amount__sum'] or 0
        option4_bet = bet_scope.bet_set.filter(choice=CHOICE_FOURTH).aggregate(Sum('amount'))['amount__sum'] or 0
        total_bet = option1_bet + option2_bet + option3_bet + option4_bet
        option1_benefit = total_bet - option1_bet * bet_scope.option_1_rate
        option2_benefit = total_bet - option2_bet * bet_scope.option_2_rate
        option3_benefit = total_bet - option3_bet * bet_scope.option_3_rate
        option4_benefit = total_bet - option4_bet * bet_scope.option_4_rate
        context = dict(
            self.admin_site.each_context(request),
            bet_scope=bet_scope,
            option_bets=(option1_bet, option2_bet, option3_bet, option4_bet),
            option_benefits=(option1_benefit, option2_benefit, option3_benefit, option4_benefit),
            choice_list=(CHOICE_FIRST, CHOICE_SECOND, CHOICE_THIRD, CHOICE_FOURTH)
        )
        return render(request, 'admin/bet_scope_detail.html', context)

    # noinspection PyMethodMayBeStatic
    def lock_bet_scope(self, request, bet_scope_id, red=False):
        request.current_app = self.admin_site.name
        bet_scope = get_object_or_404(BetScope, pk=bet_scope_id)
        bet_scope.locked = True
        bet_scope.save()
        if red:
            return redirect(red)
        return redirect('admin:bet_option')

    # noinspection PyMethodMayBeStatic
    def set_bet_winner(self, request, bet_scope_id, winner, red=False):
        request.current_app = self.admin_site.name
        bet_scope = get_object_or_404(BetScope, pk=bet_scope_id)
        bet_scope.winner = winner
        bet_scope.save()
        if red:
            return redirect(red)
        return redirect('admin:bet_option')

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('bet_option/', self.bet_option, name='bet_option'),
            path('bet_option_detail/<int:bet_scope_id>/', self.bet_scope_detail, name='bet_scope_detail'),
            path('lock_betscope/<int:bet_scope_id>/', self.lock_bet_scope, name='lock_bet_scope'),
            path('lock_betscope/<int:bet_scope_id>/<str:red>/', self.lock_bet_scope, name='lock_bet_scope'),
            path('set_winner/<int:bet_scope_id>/<str:winner>/', self.set_bet_winner, name='set_winner'),
            path('set_winner/<int:bet_scope_id>/<str:winner>/<str:red>/', self.set_bet_winner, name='set_winner'),
        ]
        return my_urls + urls

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        form.base_fields['match'].initial = request.GET.get('match_id')
        return form


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['game_name', 'title', 'start_time', 'live', 'bet_scopes', 'add']
    search_fields = ['game_name', 'title', 'start_time']
    list_filter = ['game_name', 'start_time', 'end_time']
    fieldsets = (
        ('Basic Information', {
            'fields': ['game_name', 'title']
        }),
        ('Date Time information', {
            'fields': ['start_time', 'end_time']
        }),
        ('Extra Info', {
            'classes': ('collapse',),
            'fields': ('locked',)
        })
    )

    @admin.display(boolean=True)
    def live(self, match: Match) -> bool:
        return not match.is_locked()

    # noinspection PyMethodMayBeStatic
    def bet_scopes(self, match: Match):
        return format_html('<a href="/admin/betting/betscope/?match__id__exact={}">{} scope(s)</a>', match.id,
                           match.betscope_set.count())

    # noinspection PyMethodMayBeStatic
    def add(self, match):
        return format_html('<a href="/admin/betting/betscope/add/?match_id={}">add</a>', match.id)

    def match(self, request):
        request.current_app = self.admin_site.name
        context = dict(
            self.admin_site.each_context(request),
            match_list=Match.objects.filter(end_time__gte=timezone.now())
        )

        return render(request, 'admin/match.html', context)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('match/', self.match, name='match'),
        ]
        return my_urls + urls

    def get_queryset(self, request):
        return Match.objects.prefetch_related('betscope_set').all()


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
        return format_html('<a href=/admin/betting/betscope/{}/change/>{}</a>', bet.bet_scope.id, bet.bet_scope)

    def get_queryset(self, request):
        return Bet.objects.select_related('user', 'bet_scope').all()


@admin.register(DepositWithdrawMethod)
class DepositWithdrawMethodAdmin(admin.ModelAdmin):
    list_display = ['code', 'name']


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'method', 'amount', 'verified')
    list_filter = ('method',)
    autocomplete_fields = ('user',)

    def deposit(self, request):
        request.current_app = self.admin_site.name
        context = dict(
            self.admin_site.each_context(request),
            unverified_deposits=Deposit.objects.select_related('user').exclude(verified=True)
        )

        return render(request, 'admin/deposit.html', context)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('deposit/', self.deposit, name='deposit'),
        ]
        return my_urls + urls

    def get_queryset(self, request):
        return Deposit.objects.select_related('user').all()


@admin.register(Withdraw)
class WithdrawAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'method', 'amount', 'verified')
    list_filter = ('method',)
    autocomplete_fields = ('user',)

    def withdraw(self, request):
        request.current_app = self.admin_site.name
        context = dict(
            self.admin_site.each_context(request),
            unverified_withdraws=Withdraw.objects.select_related('user').exclude(verified=True)
        )

        return render(request, 'admin/withdraw.html', context)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('withdraw/', self.withdraw, name='withdraw'),
        ]
        return my_urls + urls

    def get_queryset(self, request):
        return Withdraw.objects.select_related('user').all()


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('user', 'to', 'amount', 'verified')
    autocomplete_fields = ('user', 'to',)

    def transfer(self, request):
        request.current_app = self.admin_site.name
        context = dict(
            self.admin_site.each_context(request),
            unverified_transfers=Transfer.objects.select_related('user', 'to').exclude(verified=True)
        )

        return render(request, 'admin/transfer.html', context)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('transfer/', self.transfer, name='transfer'),
        ]
        return my_urls + urls

    def get_queryset(self, request):
        return Transfer.objects.select_related('user', 'to').all()


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('id', 'text', 'expired')
