from rest_framework import permissions

from iam.models import Membership


class UserObjectPermission(permissions.BasePermission):
    """
    Staff members can create/update/delete users. Users can update/delete themselves.
    """

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            if request.method == 'POST':
                return request.user.is_staff or request.user.is_superuser
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        return (
            request.method in permissions.SAFE_METHODS
            or request.user.is_staff or request.user.is_superuser
            or obj == request.user
        )


class GroupObjectPermission(permissions.BasePermission):
    """
    Staff members can create groups. Groups can be updated by managers, deleted by owners.
    """

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            if request.method == 'POST':
                return request.user.is_staff or request.user.is_superuser
            return True
        else:
            return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        if request.method == 'DELETE':
            allowed_roles = ['owner']
        elif request.method in ['PUT', 'PATCH']:
            allowed_roles = ['manager', 'owner']
        else:
            # TODO: every logged-in users can read now, but this should be enhanced.
            allowed_roles = ['member', 'manager', 'owner']
            return True
        return obj.membership_set.filter(
            role__in=allowed_roles,
            deleted_at__isnull=True,
            user__deleted_at__isnull=True,
            user__pk=request.user.pk,
        ).exists()


class MembershipObjectPermission(permissions.BasePermission):
    """
    Staff members can create groups. Groups can be updated by managers, deleted by owners.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS or request.user.is_superuser:
            return True
        if obj.user.pk == request.user.pk:
            return True

        if obj.role == 'member':
            allowed_roles = ['manager', 'owner']
        else:
            allowed_roles = ['owner']
        return Membership.objects.filter(
            role__in=allowed_roles,
            group__pk=obj.group.pk,
            user__pk=request.user.pk,
        ).exists()
