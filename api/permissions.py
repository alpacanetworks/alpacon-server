from rest_framework import permissions
from rest_framework.permissions import DjangoModelPermissions


class EnhancedDjangoModelPermissions(DjangoModelPermissions):
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': ['%(app_label)s.view_%(model_name)s'],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }


class SuperuserWriteOnlyPermission(permissions.BasePermission):
    """
    Only superusers are allowed to access unsafe methods (e.g., POST). Other users can still access safe methods (e.g., GET).
    """

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            return bool(
                request.method in permissions.SAFE_METHODS
                or request.user.is_superuser
            )
        else:
            return False


class AdminWriteOnlyPermission(permissions.BasePermission):
    """
    Only staff members are allowed to access unsafe methods (e.g., POST). Other users can still access safe methods (e.g., GET).
    """

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            return bool(
                request.method in permissions.SAFE_METHODS
                or request.user.is_staff
            )
        else:
            return False
