from django.contrib import admin

from .models import Club, User


# noinspection PyMethodMayBeStatic
@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ['name', 'admin', 'id']

    def admin(self, club: Club):
        return club.admin.username


# noinspection PyMethodMayBeStatic
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'balance', 'user_club', 'club_admin', 'id']
    list_filter = ['user_club']

    @admin.display(boolean=True)
    def club_admin(self, user: User):
        return bool(user.club)
