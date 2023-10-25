import re
import logging
import ldap

from django.contrib.auth import get_user_model, password_validation
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from iam.models import Group, Membership
from iam.utils import get_ldap_admin_connection
from proc.models import SystemUser, SystemGroup


logger = logging.getLogger(__name__)


User = get_user_model()

username_regex = re.compile(r'^[a-z][a-z0-9_-]*$')


DISALLOWED_USERNAMES = [
    'alpacon', 'alpamon', 'alpaca',
    'root', 'admin', 'adm', 'sys', 'bin', 'daemon', 'sync', 'www-data', 'mail',
    'nobody', 'nogroup', 'syslog', 'backup', 'news', 'games', 'lp', 'man', 'irc',
    'ubuntu', 'centos', 'ec2-user',
]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'password', 'first_name', 'last_name',
            'email', 'phone', 'tags', 'description', 'num_groups',
            'uid', 'shell', 'home_directory',
            'is_active', 'is_staff', 'is_superuser', 'is_ldap_user',
            'date_joined', 'last_login', 'last_login_ip', 'added_at', 'updated_at'
        ]
        read_only_fields = ['id', 'uid', 'home_directory', 'date_joined', 'last_login']
        extra_kwargs = {
            'is_active': {'initial': True},
            'username': {
                'help_text': _('Required. 150 characters or fewer. Lowercase letters, digits and -/_ only for UNIX environments.')
            },
            'password': {
                'write_only': True,
                'style': {'input_type': 'password'},
                'label': _('New password'),
                'help_text': password_validation.password_validators_help_text_html
            },
        }

    def validate_is_ldap_user(self, value):
        # Perform this validation only when creating a new LDAP user.
        if value:
            try:
                conn = get_ldap_admin_connection()
                conn.unbind_s()
            except ldap.SERVER_DOWN:
                raise ValidationError("Unable to connect to the LDAP server.")
            except ldap.LDAPError as e:
                raise ValidationError(f"LDAP Error: {str(e)}")
            except Exception as e:
                logger.exception(e)

        return value

    def validate_username(self, value):
        if not username_regex.match(value):
            raise ValidationError(_(
                'Enter a valid username for UNIX environment. '
                'This value may contain only lowercase letters, numbers, and -/_ characters.'
            ))
        if value in DISALLOWED_USERNAMES:
            raise ValidationError(_('Please use another username as it is disallowed.'))
        if (
            SystemUser.objects.filter(username=value).exists()
            or SystemGroup.objects.filter(groupname=value).exists()
        ):
            raise ValidationError(_('Please use another username as it is in use.'))
        return value

    def validate_password(self, value):
        if value:
            password_validation.validate_password(value, self.instance)
            return value
        else:
            return None

    def create(self, validated_data):
        instance = User.objects.create_user(**validated_data)
        if instance.is_ldap_user:
            instance.create_ldap_user(password=validated_data['password'])

        return instance

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            if validated_data['password']:
                instance.set_password(validated_data['password'])
            del validated_data['password']

        if instance.is_ldap_user:
            instance.update_ldap_user(validated_data)

        return super().update(instance, validated_data)


class UserListSerializer(UserSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name',
            'email', 'phone', 'tags', 'num_groups',
            'uid', 'is_active', 'is_staff', 'is_superuser', 'is_ldap_user',
            'date_joined',
        ]
        read_only_fields = ['id', 'uid', 'is_ldap_user']


class UserUpdateSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        read_only_fields = ['id', 'username', 'uid', 'home_directory', 'date_joined', 'last_login']
        extra_kwargs = {
            'password': {
                'write_only': True,
                'allow_blank': True,
                'style': {'input_type': 'password'},
                'label': _('New password'),
                'help_text': password_validation.password_validators_help_text_html
            },
        }

    def validate_is_ldap_user(self, value):
        # Perform validation only for users who are setting their LDAP status to true or who already had it set to true.
        if value or self.instance.is_ldap_user:

            user_dn = settings.AUTH_LDAP_USER_DN_TEMPLATE % {'user': self.instance.username}
            try:
                conn = get_ldap_admin_connection()
                conn.search_s(user_dn, ldap.SCOPE_BASE)
            except ldap.SERVER_DOWN:
                raise ValidationError("Unable to connect to the LDAP server.")
            except ldap.NO_SUCH_OBJECT:
                raise ValidationError(f"No such user in LDAP Server: {self.instance.username}")
            except ldap.LDAPError as e:
                raise ValidationError(f"Failed to update info with DN: {user_dn} to LDAP. Error: {str(e)}")

            try:
                conn.unbind_s()
            except Exception as e:
                logger.exception(e)

        return value


class SelfUserUpdateSerializer(UserUpdateSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('password')


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = [
            'id', 'name', 'display_name', 'tags', 'description', 'num_members',
            'gid', 'is_ldap_group', 'servers', 'servers_names', 'added_at', 'updated_at'
        ]
        read_only_fields = ['id', 'gid']
        extra_kwargs = {
            'name': {
                'help_text': _('Required. 150 characters or fewer. Lowercase letters, digits and -/_ only for UNIX environments.')
            },
            'servers': {
                'required': False,
            }
        }

    def validate_name(self, value):
        if not username_regex.match(value):
            raise ValidationError(_(
                'Enter a valid groupname for UNIX environment. '
                'This value may contain only lowercase letters, numbers, and -/_ characters.'
            ))

        if value in DISALLOWED_USERNAMES:
            raise ValidationError(_('Please use another name as it is disallowed.'))
        if (
            SystemUser.objects.filter(username=value).exists()
            or SystemGroup.objects.filter(groupname=value).exists()
        ):
            raise ValidationError(_('Please use another name as it is in use.'))
        return value

    def validate_is_ldap_group(self, value):
        if value:
            try:
                conn = get_ldap_admin_connection()
                conn.unbind_s()
            except ldap.SERVER_DOWN:
                raise ValidationError("Unable to connect to the LDAP server.")
            except ldap.LDAPError as e:
                raise ValidationError(f"LDAP Error: {str(e)}")
            except Exception as e:
                logger.exception(e)

        return value

    def create(self, validated_data):
        group_instance = super().create(validated_data)
        if group_instance.is_ldap_group:
            group_instance.create_ldap_group()

        return group_instance


class GroupListSerializer(GroupSerializer):
    class Meta(GroupSerializer.Meta):
        fields = [
            'id', 'name', 'display_name', 'tags', 'num_members', 'gid', 'is_ldap_group', 'servers', 'servers_names'
        ]


class GroupUpdateSerializer(GroupSerializer):
    class Meta(GroupSerializer.Meta):
        read_only_fields = ['id', 'name', 'gid', 'id_ldap_group']


    def validate_is_ldap_group(self, value):
        if value or self.instance.is_ldap_group:

            group_dn = settings.AUTH_LDAP_USER_DN_TEMPLATE % {'user': self.instance.name}
            try:
                conn = get_ldap_admin_connection()
                conn.search_s(group_dn, ldap.SCOPE_BASE)
            except ldap.SERVER_DOWN:
                raise ValidationError("Unable to connect to the LDAP server.")
            except ldap.NO_SUCH_OBJECT:
                raise ValidationError(f"No such group in LDAP Server: {self.instance.name}")
            except ldap.LDAPError as e:
                raise ValidationError(f"Failed to update info with DN: {group_dn} to LDAP. Error: {str(e)}")

            try:
                conn.unbind_s()
            except Exception as e:
                logger.exception(e)

        return value


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ['id', 'group', 'group_name', 'user', 'user_name', 'role', 'added_at', 'updated_at']
        read_only_fields = ['id']

    def validate_group(self, value):
        if value.name == 'alpacon':
            raise serializers.ValidationError(
                _('Memberships for default group "alpacon" cannot be changed.')
            )
        return value

    def create(self, validated_data):
        instance = Membership.objects.create(**validated_data)

        if instance.group.is_ldap_group and instance.user.is_ldap_user:
            instance.add_ldap_group_member()

        return instance


class MembershipListSerializer(MembershipSerializer):
    class Meta:
        model = Membership
        fields = ['id', 'group', 'group_name', 'user', 'user_name', 'role']


class MembershipUpdateSerializer(MembershipSerializer):
    class Meta(MembershipSerializer.Meta):
        read_only_fields = ['id', 'group', 'user']
