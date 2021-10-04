from django.contrib import admin

from betting.models import ConfigModel


@admin.register(ConfigModel)
class ConfigModelAdmin(admin.ModelAdmin):
    pass
