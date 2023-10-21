from rest_framework import permissions


class SessionObjectPermission(permissions.BasePermission):
    """
    Only session user can update.
    """

    def has_object_permission(self, request, view, obj):
        if (
            request.method in permissions.SAFE_METHODS
            or request.user.pk == obj.user.pk
        ):
            return True
