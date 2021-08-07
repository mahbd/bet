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


class IsOwnerOrAdminOrReadOnly(IsAdminOrReadOnly):
    def has_object_permission(self, request, view, obj):
        return bool(
            request.method in SAFE_METHODS or
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or obj.admin_id == request.user.id)
        )


class IsOwnerOrAdminOrCreateOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        response = bool(
            request.method not in ['GET', 'PUT'] or
            request.user and
            request.user.is_superuser
        )
        print("Permission response", response)
        return response

    def has_object_permission(self, request, view, obj):
        response = bool(
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or obj.admin_id == request.user.id)
        )
        print("Permission response objects", response)
        return response
