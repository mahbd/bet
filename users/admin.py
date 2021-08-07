from django.contrib import admin

from .models import Club, User


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    pass


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    pass
