from django.utils.html import format_html

from bet import admin
from .models import Club, User


# noinspection PyMethodMayBeStatic
@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    autocomplete_fields = ['admin']
    list_display = ['id', 'name', 'balance', 'club_admin', 'total_users']
    list_per_page = 20
    search_fields = ['name']

    def admin(self, club: Club):
        return club.admin.username

    def total_users(self, club: Club):
        return format_html('<a href=/admin/users/user/?user_club__id__exact={}>{} user(s)</a>', club.id,
                           club.user_set.count())

    def club_admin(self, club: Club):
        if club.admin is None:
            return "None"
        return format_html('<a href=/admin/users/user/{}/change/>{}</a>', club.admin_id, club.admin.username)

    def get_queryset(self, request):
        return Club.objects.prefetch_related('user_set').select_related('admin').all()


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
            'fields': ['password', 'last_login', 'groups', 'is_superuser', 'referred_by']
        })
    )

    def get_queryset(self, request):
        return User.objects.select_related('club', 'user_club').all()

    @admin.display(boolean=True)
    def club_admin(self, user: User):
        return user.is_club_admin()
