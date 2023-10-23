import logging
import ldap

from django.db import models
from django.db.models.aggregates import Max
from django.db.models.functions import Coalesce
from django.contrib.auth.models import AbstractUser, UserManager
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string

from phonenumber_field.modelfields import PhoneNumberField

from iam.utils import get_ldap_admin_connection, get_ldap_user_connection
from utils.models import UUIDBaseModel

logger = logging.getLogger(__name__)

DUMMY_USER_FOR_GROUPS = b'cn=nobody,dc=dummy,dc=com'


class MyUserManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().filter(
            deleted_at__isnull=True,
        )


class GroupManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(
            deleted_at__isnull=True,
        )


class MembershipManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(
            deleted_at__isnull=True,
            group__deleted_at__isnull=True,
            user__deleted_at__isnull=True,
        )


class User(AbstractUser, UUIDBaseModel):
    phone = PhoneNumberField(
        _('phone number'),
        blank=True,
        help_text=_(
            'Phone number should start with a country code (e.g., +00). '
            'We use this phone number to contact you for two-step verifications or various notifications.'
        )
    )
    tags = models.CharField(
        _('tags'),
        max_length=128, default='', blank=True,
        help_text=_(
            'Add tags for this user so that people can find easily. '
            'Tags should start with "#" and be comma-separated.'
        )
    )
    description = models.TextField(
        _('description'),
        default='', blank=True,
        help_text=_('Markdown is supported.')
    )
    groups = models.ManyToManyField(
        'iam.Group',
        through='iam.Membership',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name='users',
        related_query_name='user',
    )
    uid = models.PositiveIntegerField(
        _('UID'),
        unique=True, null=True, blank=True,
        help_text=_(
            'This UID will be used when creating an account on a server. '
            'This value should be unique. If this field is blank, we will '
            'automatically assign a unique value starting from 2000.'
        )
    )
    shell = models.CharField(
        _('shell'),
        max_length=64, blank=True,
        default='/bin/bash',
        help_text=_(
            'An absolute path for a shell of choice.'
        )
    )
    home_directory = models.CharField(
        _('home directory'),
        max_length=128, blank=True,
        default='',
        help_text=_(
            'An absolute path for the user\'s home directory. '
            'If this field is blank, "/home/<username>/" will be the default.'
        )
    )
    is_ldap_user = models.BooleanField(
        _('LDAP status'),
        default=False,
        help_text=_('Designates that this user is a LDAP user.')
    )

    objects = MyUserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        get_latest_by = 'added_at'

    def __str__(self):
        return self.get_full_name() or self.username

    def save(self, *args, **kwargs):
        if self.is_superuser and not self.is_staff:
            self.is_staff = True
        if not self.uid:
            self.uid = User.objects.aggregate(
                uid_max=Coalesce(Max('uid'), 1999)
            )['uid_max'] + 1
        if not self.home_directory:
            self.home_directory = '/home/' + self.username
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_ldap_user:
            # 1. Delete membership - ensure to remove ldap group membership
            memberships = self.membership_set.filter(deleted_at__isnull=True)
            for membership in memberships:
                membership.delete()
            # 2. Delete LDAP user
            self.delete_ldap_user()

        # TODO: delete system users in background
        for sysuser_obj in self.systemuser_set.all():
            cmd = sysuser_obj.server.del_user(
                self,
                run_after=[],
            )

        self.membership_set.filter(
            deleted_at__isnull=True
        ).delete()
        self.apitoken_set.all().delete()
        self.username = 'deleted_user-%(name)s-%(rand)s' % {
            'name': self.username,
            'rand': get_random_string(16),
        }
        self.uid = None
        self.is_active = False
        self.set_unusable_password()
        self.deleted_at = timezone.now()
        super().save(update_fields=['username', 'password', 'uid', 'is_active', 'deleted_at'])

    @property
    def num_groups(self):
        return self.get_memberships().count()

    @property
    def last_login_ip(self):
        activity = self.activity_set.first()
        if activity:
            return activity.ip
        else:
            return None

    def get_memberships(self):
        return self.membership_set.filter(
            deleted_at__isnull=True,
            group__deleted_at__isnull=True,
        )

    def check_password(self, raw_password):
        if self.is_ldap_user:
            return self.check_ldap_password(raw_password)

        return super().check_password(raw_password)

    def set_password(self, raw_password):
        if self.is_ldap_user:
            return self.update_ldap_password(raw_password)

        super().set_password(raw_password)

    def create_ldap_user(self, password):
        logger.info('Creating LDAP user %s...', self.username)

        # set user attributes
        user_dn = settings.AUTH_LDAP_USER_DN_TEMPLATE % {'user': self.username}
        user_attrs = [
            ('objectclass', [b'inetOrgPerson', b'posixAccount', b'top']),
            ('uid', [self.username.encode()]),
            ('cn', [self.get_full_name().encode()]),
            ('sn', [self.last_name.encode()]),
            ('givenName', [self.first_name.encode()]),
            ('uidnumber', [str(self.uid).encode()]),
            ('gidnumber', [str(Group.get_default().gid).encode()]),
            ('homedirectory', [self.home_directory.encode()]),
            ('loginshell', [self.shell.encode()]),
            ('mail', [self.email.encode()]),
        ]
        logger.debug('Attributes: %s', user_attrs)

        conn = None
        try:
            conn = get_ldap_admin_connection()
            conn.add_s(user_dn, user_attrs)
            conn.passwd_s(user_dn, None, password)
            logger.info('Successfully created LDAP user %s.', self.username)
        # Account registration was successful, but an error occurred within LDAP
        except ldap.LDAPError as e:
            logger.debug(f"Failed to add user with DN: {user_dn} to LDAP. Error: {str(e)}")
            self.is_ldap_user = False

        if conn:
            try:
                conn.unbind_s()
            except ldap.LDAPError as e:
                logger.debug(f"Disconnect failed after creating user: {user_dn}. Error: {str(e)}")

        self.set_unusable_password()
        self.save(update_fields=['password'])

    def check_ldap_password(self, password):
        user_dn = settings.AUTH_LDAP_USER_DN_TEMPLATE % {'user': self.username}

        conn = None
        try:
            conn = get_ldap_user_connection(user_dn, password)
            result = True
        except ldap.LDAPError:
            result = False

        if conn:
            try:
                conn.unbind_s()
            except ldap.LDAPError as e:
                logger.debug(f"Disconnect failed after checking password : {user_dn}. Error: {str(e)}")

        return result

    def update_ldap_password(self, password):
        user_dn = settings.AUTH_LDAP_USER_DN_TEMPLATE % {'user': self.username}

        conn = None
        try:
            conn = get_ldap_admin_connection()
            conn.passwd_s(user_dn, None, password)
            logger.info('Changed LDAP password of %s.', self.username)
        except ldap.LDAPError as e:
            logger.debug(f"Failed to update password with DN: {user_dn} to LDAP. Error: {str(e)}")

        if conn:
            try:
                conn.unbind_s()
            except ldap.LDAPError as e:
                logger.debug(f"Disconnect failed after updating password: {user_dn}. Error: {str(e)}")

        self.set_unusable_password()
        self.save(update_fields=['password'])

    def update_ldap_user(self, validated_data):
        logger.info('Updating LDAP user %s...', self.username)

        user_dn = settings.AUTH_LDAP_USER_DN_TEMPLATE % {'user': self.username}

        mod_attrs = [
            (ldap.MOD_REPLACE, 'loginshell', validated_data['shell'].encode()),
            (ldap.MOD_REPLACE, 'givenName', validated_data['first_name'].encode()),
            (ldap.MOD_REPLACE, 'sn', validated_data['last_name'].encode()),
            (ldap.MOD_REPLACE, 'cn', f"{validated_data['first_name']} {validated_data['last_name']}".encode()),
            (ldap.MOD_REPLACE, 'mail', validated_data['email'].encode()),
        ]

        conn = None
        try:
            conn = get_ldap_admin_connection()
            conn.modify_s(user_dn, mod_attrs)
            logger.info('Successfully updated LDAP user of %s.', self.username)
        except ldap.LDAPError as e:
            logger.debug(f"Failed to update info with DN: {user_dn} to LDAP. Error: {str(e)}")

        if conn:
            try:
                conn.unbind_s()
            except ldap.LDAPError as e:
                logger.debug(f"Disconnect failed after updating user: {user_dn}. Error: {str(e)}")


    def delete_ldap_user(self):
        logger.info('Deleting LDAP user %s...', self.username)

        user_dn = settings.AUTH_LDAP_USER_DN_TEMPLATE % {'user': self.username}

        conn = None
        try:
            conn = get_ldap_admin_connection()
            conn.delete_s(user_dn)
            logger.info('Successfully deleted LDAP user %s (%s).', self.username, user_dn)
        except ldap.LDAPError as e:
            logger.debug(f"Failed to delete user with DN: {user_dn} to LDAP. Error: {str(e)}")

        if conn:
            try:
                conn.unbind_s()
            except ldap.LDAPError as e:
                logger.debug(f"Disconnect failed after deleting user: {user_dn}. Error: {str(e)}")



class Group(UUIDBaseModel):
    name = models.SlugField(
        _('name'),
        max_length=128, unique=True,
        help_text=_(
            'A name should only use letters, numbers, "_", and "-". '
            'No special characters or whitespaces allowed.'
        )
    )
    display_name = models.CharField(
        _('display name'),
        max_length=128,
        help_text=_('This name will be used to display on the screen.')
    )
    tags = models.CharField(
        _('tags'),
        max_length=128, default='', blank=True,
        help_text=_(
            'Add tags for this group so that people can find easily. '
            'Tags should start with "#" and be comma-separated.'
        )
    )
    description = models.TextField(
        _('description'),
        default='', blank=True,
        help_text=_('Markdown is supported.')
    )
    gid = models.PositiveIntegerField(
        _('GID'),
        unique=True, null=True, blank=True,
        help_text=_(
            'This GID will be used when creating a group on a server. '
            'This value should be unique. If this field is blank, we will '
            'automatically assign a unique value starting from 2000.'
        )
    )
    is_ldap_group = models.BooleanField(
        _('LDAP status'),
        default=False,
        help_text=_('Designates that this group is a LDAP group.')
    )

    objects = GroupManager()

    class Meta:
        verbose_name = _('group')
        verbose_name_plural = _('groups')
        get_latest_by = 'added_at'

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        if not self.gid:
            self.gid = Group.objects.aggregate(
                gid_max=Coalesce(Max('gid'), 1999)
            )['gid_max'] + 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.name == 'alpacon':
            raise Exception('Default group "alpacon" cannot be removed.')

        if self.is_ldap_group:
            self.delete_ldap_group()

        # TODO: delete system groups in background
        for sysgroup_obj in self.systemgroup_set.all():
            cmd = sysgroup_obj.server.del_group(
                self,
                run_after=[],
            )

        self.membership_set.filter(
            deleted_at__isnull=True
        ).delete()
        self.name = 'deleted_group-%(name)s-%(rand)s' % {
            'name': self.name,
            'rand': get_random_string(16),
        }
        self.gid = None
        self.deleted_at = timezone.now()
        super().save(update_fields=['name', 'gid', 'deleted_at'])

    @property
    def num_members(self):
        return self.get_memberships().count()

    @property
    def servers_names(self):
        return self.servers.values_list('name', flat=True)

    @classmethod
    def get_default(cls):
        return cls.objects.get_or_create(
            name='alpacon',
            defaults={
                'display_name': _('Alpacon users'),
                'tags': '#alpacon, #default',
                'description': _(
                    'All users registered at Alpacon are members of this group by default. '
                    'As this is a system group, you cannot delete this group or update memberships.'
                )
            }
        )[0]

    def get_memberships(self):
        return self.membership_set.filter(
            deleted_at__isnull=True,
            user__deleted_at__isnull=True,
        )

    def create_ldap_group(self):
        logger.info('Creating LDAP group %s...', self.name)

        group_dn = settings.AUTH_LDAP_GROUP_DN_TEMPLATE % {'group': self.name}
        group_attrs = [
            ('objectclass', [b'groupofnames']),
            ('cn', [self.name.encode()]),
            ('member', [DUMMY_USER_FOR_GROUPS]),
        ]
        logger.debug('Attributes: %s', group_attrs)

        # add group to the ldap server
        conn = None
        try:
            conn = get_ldap_admin_connection()
            conn.add_s(group_dn, group_attrs)
            logger.info('Successfully created LDAP group %s.', self.name)
        except ldap.LDAPError as e:
            logger.debug(f"Failed to create group with DN: {group_dn} to LDAP. Error: {str(e)}")

        if conn:
            try:
                conn.unbind_s()
            except ldap.LDAPError as e:
                logger.debug(f"Disconnect failed after creating group: {group_dn}. Error: {str(e)}")


    def delete_ldap_group(self):
        logger.info('Deleting LDAP group %s...', self.name)

        group_dn = settings.AUTH_LDAP_GROUP_DN_TEMPLATE % {'group': self.name}

        conn = None
        try:
            conn = get_ldap_admin_connection()
            conn.delete_s(group_dn)
            logger.info('Successfully deleted LDAP group %s (%s).', self.name, group_dn)
        except ldap.LDAPError as e:
            logger.debug(f"Failed to delete group with DN: {group_dn} to LDAP. Error: {str(e)}")

        if conn:
            try:
                conn.unbind_s()
            except ldap.LDAPError as e:
                logger.debug(f"Disconnect failed after deleting group: {group_dn}. Error: {str(e)}")


    def update_ldap_group(self, update_instance):
        logger.info('Updating LDAP group %s...', self.name)

        group_dn = settings.AUTH_LDAP_GROUP_DN_TEMPLATE % {'group': self.name}
        mod_attrs = [
            (ldap.MOD_REPLACE, 'cn', update_instance.name().encode()),
        ]

        conn = None
        try:
            conn = get_ldap_admin_connection()
            conn.modify_s(group_dn, mod_attrs)
            logger.info('Successfully updated LDAP group  of %s (%s).', self.name, group_dn)
        except ldap.LDAPError as e:
            logger.debug(f"Failed to update group with DN: {group_dn} to LDAP. Error: {str(e)}")

        if conn:
            try:
                conn.unbind_s()
            except ldap.LDAPError as e:
                logger.debug(f"Disconnect failed after updating group: {group_dn}. Error: {str(e)}")


class Membership(UUIDBaseModel):
    ROLES = (
        ('member', _('Member')),
        ('manager', _('Manager')),
        ('owner', _('Owner')),
    )
    group = models.ForeignKey(
        'iam.Group', on_delete=models.CASCADE,
        verbose_name=_('group')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name=_('user')
    )
    role = models.CharField(
        _('role'), max_length=16,
        choices=ROLES,
        default='member',
        help_text=_('Select a role for this user in the group.')
    )

    objects = MembershipManager()

    class Meta:
        verbose_name = _('membership')
        verbose_name_plural = _('memberships')
        unique_together = ('user', 'group')

    @property
    def user_name(self):
        return str(self.user)

    @property
    def group_name(self):
        return str(self.group)

    def delete(self, *args, **kwargs):
        if self.group.is_ldap_group and self.user.is_ldap_user:
            self.delete_ldap_group_member()

        super().delete(*args, **kwargs)

    def add_ldap_group_member(self):
        # Note: `user_name` and `group_name` do not correspond to LDAP UIDs
        group_dn = settings.AUTH_LDAP_GROUP_DN_TEMPLATE % {'group': self.group.name}
        member_dn = settings.AUTH_LDAP_USER_DN_TEMPLATE % {'user': self.user.username}

        mod_attrs = [(ldap.MOD_ADD, 'member', member_dn.encode())]

        conn = None
        try:
            conn = get_ldap_admin_connection()
            conn.modify_s(group_dn, mod_attrs)
            logger.info('Added LDAP member %s to group %s', self.user.username, group_dn)
        except ldap.LDAPError as e:
            logger.debug(f"Failed to add member with DN: {group_dn} to LDAP. Error: {str(e)}")

        if conn:
            try:
                conn.unbind_s()
            except ldap.LDAPError as e:
                logger.debug(f"Disconnect failed after adding member: {group_dn}. Error: {str(e)}")

    def delete_ldap_group_member(self):
        group_dn = settings.AUTH_LDAP_GROUP_DN_TEMPLATE % {'group': self.group.name}
        member_dn = settings.AUTH_LDAP_USER_DN_TEMPLATE % {'user': self.user.username}

        mod_attrs = [(ldap.MOD_DELETE, 'member', member_dn.encode())]

        conn = None
        try:
            conn = get_ldap_admin_connection()
            conn.modify_s(group_dn, mod_attrs)
            logger.info('Deleted LDAP member %s from group %s.', self.user.username, group_dn)
        except ldap.LDAPError as e:
            logger.debug(f"Failed to delete member with DN: {group_dn} to LDAP. Error: {str(e)}")

        if conn:
            try:
                conn.unbind_s()
            except ldap.LDAPError as e:
                logger.debug(f"Disconnect failed after deleting member: {group_dn}. Error: {str(e)}")
