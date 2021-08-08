from django.contrib import admin

from .models import Club, User


# noinspection PyMethodMayBeStatic
@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_display = ['name', 'admin', 'id']
    autocomplete_fields = ['admin']

    def admin(self, club: Club):
        return club.admin.username


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
            'fields': ['last_login', 'groups', 'user_permissions', 'is_superuser', 'referred_by', 'refer_set']
        })
    )

    @admin.display(boolean=True)
    def club_admin(self, user: User):
        return bool(user.club)
