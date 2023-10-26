from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied, ValidationError

from api.apitoken.auth import APITokenAuthentication

from iam.models import Group, Membership
from iam.api.serializers import (
    UserSerializer, UserListSerializer, UserUpdateSerializer, SelfUserUpdateSerializer,
    GroupSerializer, GroupListSerializer, GroupUpdateSerializer,
    MembershipSerializer, MembershipListSerializer, MembershipUpdateSerializer,
)
from iam.api.permissions import UserObjectPermission, GroupObjectPermission, MembershipObjectPermission


User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.order_by('-is_superuser', '-is_staff', 'first_name')
    serializer_class = UserSerializer
    authentication_classes = [SessionAuthentication, APITokenAuthentication]
    permission_classes = [UserObjectPermission]
    filterset_fields = ['is_active', 'is_staff', 'is_superuser', 'is_ldap_user', 'shell']
    search_fields = ['id', 'username', 'first_name', 'last_name', 'email', 'phone', 'tags', 'description', 'uid']

    def get_object(self):
        if self.kwargs['pk'] == '-':
            return self.request.user
        else:
            return super().get_object()

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            if self.kwargs['pk'] != '-' and (self.request.user.is_staff or self.request.user.is_superuser):
                return UserUpdateSerializer
            else:
                return SelfUserUpdateSerializer
        else:
            return super().get_serializer_class()

    def perform_create(self, serializer):
        if (
            serializer.validated_data.get('is_staff', False)
            or serializer.validated_data.get('is_superuser', False)
        ) and not self.request.user.is_superuser:
            raise PermissionDenied(_('Requires superuser to assign staff or superuser privilege.'))
        return super().perform_create(serializer)

    def perform_update(self, serializer):
        if (
            serializer.validated_data.get('is_staff', False)
            or serializer.validated_data.get('is_superuser', False)
        ) and not self.request.user.is_superuser:
            raise PermissionDenied(_('Requires superuser to assign staff or superuser privilege.'))

        if (
            serializer.instance.is_superuser
            and not serializer.validated_data.get('is_superuser', serializer.instance.is_superuser)
            and User.objects.filter(
                is_superuser=True
            ).count() <= 1
        ):
            raise ValidationError({
                'non_field_errors': [
                    _('There should be at least a superuser in the system.'),
                ]
            })

        return super().perform_update(serializer)

    def perform_destroy(self, instance):
        if (
            instance.pk != self.request.user.pk
            and (instance.is_staff or instance.is_superuser)
            and not self.request.user.is_superuser
        ):
            raise PermissionDenied(_('Requires superuser to delete staff or above.'))

        for membership in Membership.objects.filter(
            user__pk=instance.pk,
            role='owner',
        ):
            if Membership.objects.filter(
                group__pk=membership.group.pk,
                role='owner',
            ).count() <= 1:
                raise ValidationError({
                    'non_field_errors': [
                        _('This user cannot be deleted as the only owner of the group "%(group)s".') % {
                            'group': membership.group.display_name,
                        }
                    ]
                })

        if instance.is_superuser and User.objects.filter(
            is_superuser=True
        ).count() <= 1:
            raise ValidationError({
                'non_field_errors': [
                    _('There should be at least a superuser in the system.'),
                ]
            })

        return super().perform_destroy(instance)


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.order_by('display_name')
    serializer_class = GroupSerializer
    authentication_classes = [SessionAuthentication, APITokenAuthentication]
    permission_classes = [GroupObjectPermission]
    filterset_fields = ['is_ldap_group']
    search_fields = ['id', 'name', 'display_name', 'tags', 'description', 'gid', 'server__name']

    def get_serializer_class(self):
        if self.action == 'list':
            return GroupListSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return GroupUpdateSerializer
        else:
            return super().get_serializer_class()

    def perform_create(self, serializer):
        super().perform_create(serializer)
        serializer.instance.membership_set.create(
            user=self.request.user,
            role='owner',
        )

    def perform_destroy(self, instance):
        if instance.name == 'alpacon':
            raise ValidationError({
                'non_field_errors': [
                    _('Default group "alpacon" cannot be removed.'),
                ]
            })
        return super().perform_destroy(instance)


class MembershipViewSet(viewsets.ModelViewSet):
    queryset = Membership.objects.all()
    serializer_class = MembershipSerializer
    authentication_classes = [SessionAuthentication, APITokenAuthentication]
    permission_classes = [MembershipObjectPermission]
    pagination_class = None
    filterset_fields = ['group', 'user', 'role']

    def get_serializer_class(self):
        if self.action == 'list':
            return MembershipListSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return MembershipUpdateSerializer
        else:
            return super().get_serializer_class()

    def perform_create(self, serializer):
        if not self.request.user.is_superuser:
            if serializer.validated_data.get('role', 'member') == 'member':
                allowed_roles = ['manager', 'owner']
            else:
                allowed_roles = ['owner']
            if not Membership.objects.filter(
                role__in=allowed_roles,
                group__pk=serializer.validated_data['group'].pk,
                user__pk=self.request.user.pk,
            ).exists():
                raise PermissionDenied(_('Requires higher privilege.'))
        return super().perform_create(serializer)

    def perform_update(self, serializer):
        if not self.request.user.is_superuser:
            if not Membership.objects.filter(
                role='owner',
                group__pk=serializer.instance.group.pk,
                user__pk=self.request.user.pk,
            ).exists():
                raise PermissionDenied(_('Requires group owner.'))
        if (
            serializer.instance.role == 'owner'
            and serializer.validated_data['role'] != 'owner'
            and Membership.objects.filter(
                role='owner',
                group__pk=serializer.instance.group.pk,
            ).count() <= 1
        ):
            raise ValidationError({
                'non_field_errors': [
                    _('This user is the only owner of the group. Add another owner to proceed.'),
                ]
            })
        return super().perform_update(serializer)

    def perform_destroy(self, instance):
        if not self.request.user.is_superuser and instance.user.pk != self.request.user.pk:
            if instance.role == 'member':
                allowed_roles = ['manager', 'owner']
            else:
                allowed_roles = ['owner']
            if not Membership.objects.filter(
                role__in=allowed_roles,
                group__pk=instance.group.pk,
                user__pk=self.request.user.pk,
            ).exists():
                raise PermissionDenied(_('Requires higher privilege.'))

        if instance.group.name == 'alpacon':
            raise ValidationError({
                'non_field_errors': [
                    _('Memberships for default group "alpacon" cannot be changed.'),
                ]
            })

        if instance.role == 'owner' and Membership.objects.filter(
            role='owner',
            group__pk=instance.group.pk,
        ).count() <= 1:
            raise ValidationError({
                'non_field_errors': [
                    _('This user is the only owner of the group. Add another owner to proceed.'),
                ]
            })
        return super().perform_destroy(instance)
