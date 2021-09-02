from django.db.models import F
from django.utils.html import format_html

from bet import admin
from .models import Bet, BetScope, Match, DepositWithdrawMethod, Deposit, Withdraw, Transfer, Announcement, \
    ConfigModel, ClubTransfer, Commission


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

    def get_queryset(self, request):
        return Match.objects.prefetch_related('betscope_set').all()


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = ['id', 'bet_by', 'bet_scope_link', 'choice', 'amount', 'created_at']
    readonly_fields = ['created_at']
    list_filter = ['choice', 'bet_scope', 'user__club', 'user']
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
    list_display = ['code', 'number1', 'number2']


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'method', 'amount', 'description', 'verified',)
    list_filter = ('method',)
    autocomplete_fields = ('user',)

    def get_queryset(self, request):
        return Deposit.objects.select_related('user').all()


@admin.register(Withdraw)
class WithdrawAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'method', 'amount', 'verified')
    list_filter = ('method',)
    autocomplete_fields = ('user',)

    def get_queryset(self, request):
        return Withdraw.objects.select_related('user').all()


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'to', 'amount', 'verified')
    autocomplete_fields = ('user', 'to',)

    def get_queryset(self, request):
        return Transfer.objects.select_related('user', 'to').all()


@admin.register(ClubTransfer)
class ClubTransferAdmin(admin.ModelAdmin):
    pass


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    pass


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('id', 'text', 'expired')


@admin.register(ConfigModel)
class ConfigModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'description')
