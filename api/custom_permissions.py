from rest_framework import permissions
from rest_framework.permissions import SAFE_METHODS


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


class IsOwnerOrAdminOrReadOnly(IsAdminOrReadOnly):
    def has_object_permission(self, request, view, obj):
        return bool(
            request.method in SAFE_METHODS or
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or obj.user.id == request.user.id)
        )


class ClubPermissionClass(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return bool(
            request.method in SAFE_METHODS or
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or obj.admin.id == request.user.id)
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


class BetPermissionClass(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.id == obj.user.id or request.user.is_superuser)
        )


class TransactionPermissionClass(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        if request.method == 'DELETE' and obj.verified:
            return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.id == obj.user.id or request.user.is_superuser)
        )


class IsUserOrSuperuser(permissions.BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        response = bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or obj.id == request.user.id)
        )
        return response
