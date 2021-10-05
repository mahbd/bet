from django.contrib import admin

from .models import Logging


@admin.register(Logging)
class LogAdmin(admin.ModelAdmin):
    list_display = ('error_type', 'error_message', 'description', 'created_at')

