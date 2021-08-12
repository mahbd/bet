from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.utils.html import format_html

from betting.models import TYPE_DEPOSIT, TYPE_WITHDRAW
from betting.views import total_transaction_amount
from .models import Club, User


# noinspection PyMethodMayBeStatic
from .views import total_user_balance, total_club_balance


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

    def home(self, request):
        request.current_app = self.admin_site.name
        context = dict(
            self.admin_site.each_context(request),
            total_deposit=total_transaction_amount(t_type=TYPE_DEPOSIT),
            total_withdraw=total_transaction_amount(t_type=TYPE_WITHDRAW),
            total_user_balance=total_user_balance(),
            total_club_balance=total_club_balance(),
            developer_name='Mahmudul Alam'
        )

        return render(request, 'admin/home.html', context)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('home/', self.home, name='home'),
        ]
        return my_urls + urls
