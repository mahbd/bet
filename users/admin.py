from django.contrib import admin
from django.utils.html import format_html

from .models import Club, User


# noinspection PyMethodMayBeStatic
@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_display = ['id', 'name', 'balance', 'club_admin', 'total_users', 'total_balance']
    autocomplete_fields = ['admin']

    def admin(self, club: Club):
        return club.admin.username

    def total_users(self, club: Club):
        return format_html('<a href=/admin/users/user/?user_club__id__exact={}>{} user(s)</a>', club.id,
                           club.user_set.count())

    def club_admin(self, club: Club):
        if club.admin is None:
            return "None"
        return format_html('<a href=/admin/users/user/{}/change/>{}</a>', club.admin_id, club.admin.username)

    def total_balance(self, club: Club):
        return 0


# noinspection PyMethodMayBeStatic
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    search_fields = ['username', 'first_name', 'last_name', 'email']
    autocomplete_fields = ['user_club']
    list_display = ['username', 'email', 'balance', 'user_club', 'club_admin', 'id']
    list_filter = ['user_club']
    readonly_fields = ['date_joined']
    fieldsets = (
        ('Permissions', {
            'fields': ['is_active', 'game_editor']
        }),
        ('User information', {
            'fields': ['username', 'email', 'phone', 'first_name', 'last_name', 'balance', 'user_club', 'date_joined']
        }),
        ('Advance Options', {
            'classes': ('collapse',),
            'fields': ['password', 'last_login', 'groups', 'user_permissions', 'is_superuser', 'referred_by']
        })
    )

    @admin.display(boolean=True)
    def club_admin(self, user: User):
        return bool(user.club)
