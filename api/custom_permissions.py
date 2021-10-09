from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS

from users.backends import get_current_club


class BetPermissionClass(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.id == obj.user.id or request.user.is_superuser)
        )


class ClubPermissionClass(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.method in [*SAFE_METHODS, 'PATCH'] or
                    request.user and
                    request.user.is_authenticated and
                    request.user.is_superuser)

    def has_object_permission(self, request, view, obj):
        return bool(
            request.method in SAFE_METHODS or
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or (obj.admin and obj.admin.id == request.user.id))
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.method in SAFE_METHODS or
            request.user and
            request.user.is_authenticated and
            request.user.is_superuser
        )

    def has_object_permission(self, request, view, obj):
        return bool(
            request.method in SAFE_METHODS or
            request.user and
            request.user.is_authenticated and
            request.user.is_superuser
        )


class IsOwnerOrAdminOrReadOnly(IsAdminOrReadOnly):
    def has_object_permission(self, request, view, obj):
        return bool(
            request.method in SAFE_METHODS or
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or obj.user.id == request.user.id)
        )


class UserViewPermission(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return bool(request.method in SAFE_METHODS or
                    request.user and request.user.is_authenticated and
                    (request.user.id == obj.id or request.user.is_superuser))


class MatchPermissionClass(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.method in SAFE_METHODS or
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or request.user.game_editor)
        )

    def has_object_permission(self, request, view, obj):
        return bool(
            request.method in SAFE_METHODS or
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or request.user.game_editor)
        )


class RegisterPermissionClass(permissions.BasePermission):
    def has_permission(self, request, view):
        response = bool(
            request.method == 'POST' or
            request.user and
            request.user.is_authenticated
        )
        return response

    def has_object_permission(self, request, view, obj):
        response = bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or obj.id == request.user.id)
        )
        return response


class TransactionPermissionClass(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated:
            if request.user.is_superuser:
                return True
            if request.user == obj.user:
                if request.method != 'DELETE' or not obj.status:
                    return True
        return False


class TransferPermissionClass(permissions.BasePermission):
    def has_permission(self, request, view):
        club = get_current_club(request)
        if (request.user and request.user.is_authenticated) or club:
            return True

    def has_object_permission(self, request, view, obj):
        club = get_current_club(request)
        if club:
            if request.method != 'DELETE':
                return True
        if request.user and request.user.is_authenticated:
            if request.user.is_superuser:
                return True
            if request.user == obj.user:
                if request.method != 'DELETE':
                    return True
        return False
