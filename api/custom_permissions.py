from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS


class BetPermissionClass(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.id == obj.user.id or request.user.is_superuser)
        )


class ClubPermissionClass(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return bool(
            request.method in SAFE_METHODS or
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or obj.admin.id == request.user.id)
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


class IsUser(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        response = bool(
            request.user and
            request.user.is_authenticated and request.user.id == obj.id
        )
        return response


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
        if request.method in SAFE_METHODS or not obj.verified:
            return True
        return False
