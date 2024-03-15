from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from proc.models import *


class SystemInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemInfo
        exclude = ['id', 'current', 'server']


class OsVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OsVersion
        exclude = ['id', 'current', 'server']

    def validate_name(self, value):
        if value == 'Debian GNU/Linux':
            return 'Debian'
        elif value == 'CentOS Linux':
            return 'CentOS'
        elif value == 'Red Hat Enterprise Linux':
            return 'RHEL'
        else:
            return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs['name'] == 'CentOS' or attrs['name'] == 'RHEL':
            attrs['version'] = '%d.%d' % (attrs['major'], attrs['minor'])
        elif attrs['name'] == 'Ubuntu':
            attrs['version'] = attrs['version'].rsplit('(')[0].strip().replace(' LTS', '')
        elif attrs['name'] == 'Debian':
            attrs['version'] = attrs['version'].rsplit('(')[0].strip()

        if not attrs['platform_like']:
            attrs['platform_like'] = attrs['platform']
        return attrs


class SystemTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemTime
        fields = ['datetime', 'uptime', 'timezone', 'boot_time', 'added_at']
        read_only_fields = ['boot_time']
        extra_kwargs = {
            'datetime': {'write_only': True},
            'uptime': {'write_only': True},
        }


class LoadAverageSerializer(serializers.Serializer):
    period = serializers.CharField(max_length=16, label=_('period'))
    average = serializers.FloatField(label=_('average'))


class SystemUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        fields = ['id', 'uid', 'gid', 'username', 'description', 'directory', 'shell', 'group', 'iam_user', 'iam_group']


class SystemGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemGroup
        exclude = ['current', 'server']


class InterfaceAddressSerializer(serializers.ModelSerializer):
    interface_name = serializers.CharField(
        max_length=64,
        write_only=True,
        label=_('Interface name')
    )

    class Meta:
        model = InterfaceAddress
        fields = ['interface_name', 'address', 'mask', 'broadcast']

    def to_internal_value(self, data):
        # interface = self._server.interface_set.filter(
        #     name=data['interface']
        # ).latest()
        # data['interface'] = interface.pk if interface else None
        if not data['broadcast']:
            data['broadcast'] = None
        return super().to_internal_value(data)


class InterfaceSerializer(serializers.ModelSerializer):
    addresses = InterfaceAddressSerializer(many=True, required=False)

    class Meta:
        model = Interface
        fields = [
            'id', 'name', 'mac', 'type', 'flags', 'mtu', 'link_speed',
            'addresses', 'is_up', 'is_running', 'is_loopback', 'is_p2p'
        ]

    def create(self, validated_data):
        addresses = validated_data.pop('addresses', None)
        instance = Interface.objects.create(**validated_data)
        InterfaceAddress.objects.bulk_create(
            [InterfaceAddress(interface=instance, **item) for item in addresses]
        )
        return instance

    def update(self, instance, validated_data):
        addresses = validated_data.pop('addresses', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        instance.addresses.all().delete()
        InterfaceAddress.objects.bulk_create(
            [InterfaceAddress(interface=instance, **item) for item in addresses]
        )
        return instance


class PythonVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PythonVersion
        exclude = ['current', 'server']


class SystemPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemPackage
        exclude = ['current', 'server']


class PythonPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PythonPackage
        exclude = ['current', 'server']
