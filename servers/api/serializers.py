import logging

from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Q

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from servers.models import Server, Installer, Note
from iam.models import User, Group
from profiles.models import StarredServer
from packages.models import PythonPackageEntry
from proc.api.serializers import *


logger = logging.getLogger(__name__)


class ServerSerializer(serializers.ModelSerializer):
    starred = serializers.SerializerMethodField()
    class Meta:
        model = Server
        fields = [
            'id', 'name', 'key', 'remote_ip', 'status',
            'is_connected', 'commissioned', 'starred', 'version', 'osquery_version',
            'cpu_physical_cores', 'cpu_logical_cores', 'cpu_type', 'physical_memory',
            'os_name', 'os_version', 'load', 'uptime', 'boot_time', 'last_connectivity',
            'started_at', 'added_at', 'updated_at',
            'owner', 'owner_name', 'groups', 'groups_name',
        ]
        read_only_fields = ['id', 'status', 'commissioned', 'version', 'osquery_version']
        extra_kwargs = {
            'key': {'write_only': True, 'required': False},
        }

    def __init__(self, instance=None, *args, **kwargs):
        self._user = kwargs.pop('user', None)
        super().__init__(instance, *args, **kwargs)

    def get_starred(self, obj):
        try:
            return StarredServer.objects.get(
                server__pk=obj.pk,
                user__pk=self._user.pk,
            ).ordering
        except ObjectDoesNotExist:
            return False

    def update(self, instance, validated_data):
        if 'key' in validated_data:
            instance.set_key(validated_data['key'])
            del validated_data['key']
        return super().update(instance, validated_data)


class ServerListSerializer(ServerSerializer):
    class Meta(ServerSerializer.Meta):
        fields = [
            'id', 'name', 'remote_ip', 'status', 'is_connected', 'commissioned', 'starred',
            'cpu_physical_cores', 'cpu_logical_cores', 'cpu_type', 'physical_memory',
            'os_name', 'os_version', 'load', 'boot_time', 'owner', 'owner_name', 'groups', 'groups_name'
        ]


class ServerCreateSerializer(ServerSerializer):
    PLATFORMS = [
        ('debian', _('Debian, Ubuntu')),
        ('rhel', _('RHEL, CentOS')),
    ]
    platform = serializers.ChoiceField(
        choices=PLATFORMS,
        write_only=True,
    )
    instruction_1 = serializers.CharField(
        read_only=True,
        label=_('Installation instruction 1')
    )
    instruction_2 = serializers.CharField(
        read_only=True,
        label=_('Installation instruction 2')
    )

    class Meta(ServerSerializer.Meta):
        fields = ['name', 'platform', 'id', 'key', 'instruction_1', 'instruction_2', 'groups']

    def validate(self, attrs):
        self._package = PythonPackageEntry.objects.filter(
            package__name='alpamon',
        ).order_by(
            '-v_major', '-v_minor', '-v_patch', '-v_label'
        ).first()

        if not self._package:
            raise ValidationError({
                'non_field_errors': [
                    _('Please upload a python package for alpamon to add servers.'),
                ]
            })
        return super().validate(attrs)

    def create(self, validated_data):
        groups = validated_data.pop('groups')
        platform = validated_data.pop('platform')
        key = validated_data.pop('key', '')

        server = Server(**validated_data)
        if not key:
            key = server.make_random_key()
        server.set_key(key)
        server.save()
        server.groups.set(groups)

        if platform == 'debian':
            template_name = 'servers/install.deb.sh'
        elif platform == 'rhel':
            template_name = 'servers/install.rhel.sh'
        else:
            raise NotImplementedError

        script = render_to_string(
            template_name, {
                'alpacon_url': settings.URL_PREFIX,
                'alpamon_id': server.id,
                'alpamon_key': key,
                'package_name': self._package.name,
                'package_url': self._package.get_download_url(),
            }
        )
        installer = Installer.objects.create(server=server, content=script)
        server.instruction_1 = 'curl %(url)s | sudo -E bash' % {
            'url': settings.URL_PREFIX + installer.get_absolute_url()
        }
        server.instruction_2 = script

        return server


class ServerMetaSerializer(serializers.ModelSerializer):
    info = SystemInfoSerializer(required=False)
    os = OsVersionSerializer(required=False)
    time = SystemTimeSerializer(required=False)
    load = LoadAverageSerializer(required=False)
    users = SystemUserSerializer(many=True, required=False)
    groups = SystemGroupSerializer(many=True, required=False)
    interfaces = InterfaceSerializer(many=True, required=False)
    addresses = InterfaceAddressSerializer(many=True, required=False)
    packages = SystemPackageSerializer(many=True, required=False)
    pypackages = PythonPackageSerializer(many=True, required=False)

    class Meta:
        model = Server
        fields = ['version', 'osquery_version', 'info', 'os', 'time', 'load', 'users', 'groups', 'interfaces', 'addresses', 'packages', 'pypackages']

    def save(self, *args, **kwargs):
        update_fields = ['updated_at']
        if 'version' in self.validated_data:
            self.instance.version = self.validated_data['version']
            update_fields.append('version')
        if 'osquery_version' in self.validated_data:
            self.instance.osquery_version = self.validated_data['osquery_version']
            update_fields.append('osquery_version')
        if 'load' in self.validated_data:
            self.instance.load = self.validated_data['load']['average']
            update_fields.append('load')
        self.instance.save(update_fields=update_fields)

        if 'info' in self.validated_data:
            self.instance.systeminfo_set.create(**self.validated_data['info'])
        if 'os' in self.validated_data:
            self.instance.osversion_set.create(**self.validated_data['os'])
        if 'time' in self.validated_data:
            self.instance.systemtime_set.create(**self.validated_data['time'])

        if 'groups' in self.validated_data and 'users' in self.validated_data:
            self.instance.systemuser_set.all().delete()
            self.instance.systemgroup_set.all().delete()

            groups = []
            for item in self.validated_data['groups']:
                try:
                    iam_group = Group.objects.get(gid=item['gid'], name=item['groupname'])
                except ObjectDoesNotExist:
                    iam_group = None
                groups.append(SystemGroup(server=self.instance, iam_group=iam_group, **item))
            SystemGroup.objects.bulk_create(groups)

            users = []
            for item in self.validated_data['users']:
                try:
                    iam_user = User.objects.get(uid=item['uid'], username=item['username'])
                except:
                    iam_user = None
                systemgroup = None
                for group in groups:
                    if group.gid == item['gid']:
                        systemgroup = group
                        break
                users.append(SystemUser(
                    server=self.instance,
                    iam_user=iam_user,
                    group=systemgroup,
                    **item
                ))
            SystemUser.objects.bulk_create(users)

        if 'interfaces' in self.validated_data and 'addresses' in self.validated_data:
            self.instance.interface_set.all().delete()
            interfaces = Interface.objects.bulk_create(
                [Interface(server=self.instance, **item) for item in self.validated_data['interfaces']]
            )
            interface_map = {}
            for obj in interfaces:
                interface_map[obj.name] = obj
            InterfaceAddress.objects.bulk_create(
                [InterfaceAddress(
                    interface=interface_map[item['interface_name']],
                    address=item['address'],
                    mask=item['mask'],
                    broadcast=item['broadcast'],
                ) for item in self.validated_data['addresses']]
            )
        
        if 'packages' in self.validated_data:
            self.instance.systempackage_set.all().delete()
            SystemPackage.objects.bulk_create(
                [SystemPackage(server=self.instance, **item) for item in self.validated_data['packages']]
            )

        if 'pypackages' in self.validated_data:
            self.instance.pythonpackage_set.all().delete()
            PythonPackage.objects.bulk_create(
                [PythonPackage(server=self.instance, **item) for item in self.validated_data['pypackages']]
            )


class ServerActionSerializer(serializers.Serializer):
    ACTIONS = (
        ('update_information', _('Update system information')),
        ('upgrade_system', _('Upgrade system')),
        ('reboot_system', _('Reboot system')),
        ('shutdown_system', _('Shutdown system')),
        ('upgrade_agent', _('Upgrade agent')),
        ('restart_agent', _('Restart agent')),
        ('shutdown_agent', _('Shutdown agent')),
    )

    action = serializers.ChoiceField(
        choices=ACTIONS,
        label=_('Action')
    )

    def __init__(self, instance=None, *args, **kwargs):
        self._user = kwargs.pop('user', None)
        super().__init__(instance, *args, **kwargs)

    def validate(self, attrs):
        if not self.instance.commissioned:
            raise ValidationError(
                _('Requested server is not commisioned yet. Please finish the installation steps first.')
            )
        elif not self.instance.is_connected:
            raise ValidationError(
                _('Requested server is not connected now. Please try again later.')
            )
        return super().validate(attrs)

    def save(self, *args, **kwargs):
        action = getattr(self.instance, self.validated_data['action'])
        self.command = action(requested_by=self._user)


class ServerStarStatusSerializer(serializers.Serializer):
    status = serializers.BooleanField(
        label=_('Starred status'),
        help_text=_(
            'Starred servers are shown in the home page. '
            'They are also displayed first in the server list.'
        )
    )

    def __init__(self, instance=None, *args, **kwargs):
        self._user = kwargs.pop('user', None)
        super().__init__(instance=instance, *args, **kwargs)

    def validate(self, attrs):
        if attrs['status'] and self.instance is not None:
            raise ValidationError(_('You already have starred this server.'))

        if not attrs['status'] and self.instance is None:
            raise ValidationError(_('You already have unstarred this server.'))

        if attrs['status'] and StarredServer.objects.filter(
            user__pk=self._user.pk
        ).count() >= 5:
            raise ValidationError(_('You can star up to 5 servers. Please unstar one first.'))
        return super().validate(attrs)

    def to_representation(self, instance):
        return {
            'status': self.instance is not None
        }

    def save(self, *args, **kwargs):
        if self.validated_data['status']:
            self.instance = StarredServer.objects.get_or_create(
                server=self.context['server'],
                user=self._user,
            )[0]
        else:
            if self.instance is not None:
                self.instance.delete()
                self.instance = None
        return self.instance


class RelatedServerField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        if self.context['request'].user.is_staff or self.context['request'].user.is_superuser:
            return Server.objects.all()
        else:
            return Server.objects.filter(
                Q(groups__membership__user__pk=self.context['request'].user.pk)
                | Q(owner__pk=self.context['request'].user.pk)
            ).distinct()


class InstallerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Installer
        fields = ['content']


class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ['id', 'server', 'server_name', 'author', 'author_name', 'content', 'private', 'pinned', 'updated_at']
        read_only_fields = ['id', 'server']

    def validate_pinned(self, value):
        if value and not self.instance.pinned:
            if Note.objects.filter(
                server__pk=self.instance.server.pk,
                pinned=True,
            ).count() >= 3:
                raise ValidationError(_('There can be at most 3 pinned notes. Please remove another one first.'))
        return value


class NoteCreateSerializer(serializers.ModelSerializer):
    server = RelatedServerField()

    class Meta:
        model = Note
        fields = ['id', 'server', 'author', 'content', 'private', 'pinned', 'updated_at']
        read_only_fields = ['id']

    def validate(self, attrs):
        if attrs.get('pinned', False) and Note.objects.filter(
            server__pk=attrs['server'].pk,
            pinned=True,
        ).count() >= 3:
            raise ValidationError(_('There can be at most 3 pinned notes. Please remove another one first.'))
        return super().validate(attrs)
