from django.contrib import admin

from betting.models import Bet, BetQuestion, ConfigModel, Deposit, Match, QuestionOption


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    pass


@admin.register(BetQuestion)
class BetQuestionAdmin(admin.ModelAdmin):
    pass


@admin.register(ConfigModel)
class ConfigModelAdmin(admin.ModelAdmin):
    pass


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    pass


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    pass


@admin.register(QuestionOption)
class QuestionOptionAdmin(admin.ModelAdmin):
    pass
