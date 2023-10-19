from rest_framework import permissions


class ServerObjectPermission(permissions.BasePermission):
    """
    Staff members or object owner can update or delete servers.
    """

    def has_object_permission(self, request, view, obj):
        if (
            request.method in permissions.SAFE_METHODS
            or (hasattr(request, 'client') and request.client.pk == obj.pk) # alpamon
            or request.user.is_staff or request.user.is_superuser # staff
            or request.user.pk == obj.owner.pk # owner
        ):
            return True


class NoteObjectPermission(permissions.BasePermission):
    """
    Staff members or object author can update or delete notes.
    """

    def has_object_permission(self, request, view, obj):
        if (
            request.method in permissions.SAFE_METHODS
            or (not obj.private and (request.user.is_staff or request.user.is_superuser)) # staff
            or request.user.pk == obj.author.pk # author
        ):
            return True
