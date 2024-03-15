import logging

from servers.api.mixins import ServerDataViewSet, ServerMultiDataViewSet
from proc.models import *
from proc.api.serializers import *


logger = logging.getLogger(__name__)


class SystemInfoViewSet(ServerDataViewSet):
    queryset = SystemInfo.objects.order_by('-added_at')
    serializer_class = SystemInfoSerializer
    filterset_fields = ['server', 'cpu_type', 'cpu_subtype', 'cpu_brand']
    serach_fields = ['uuid', 'cpu_type', 'cpu_subtype', 'cpu_brand', 'hardware_vendor', 'hardware_serial', 'hostname', 'local_hostname']


class OsVersionViewSet(ServerDataViewSet):
    queryset = OsVersion.objects.order_by('-added_at')
    serializer_class = OsVersionSerializer
    filterset_fields = ['server', 'name', 'version', 'platform', 'platform_like']
    search_fields = ['name', 'version', 'platform', 'platform_like']


class SystemTimeViewSet(ServerDataViewSet):
    queryset = SystemTime.objects.order_by('-added_at')
    serializer_class = SystemTimeSerializer
    filterset_fields = ['server', 'timezone']


class SystemUserViewSet(ServerMultiDataViewSet):
    queryset = SystemUser.objects.all()
    serializer_class = SystemUserSerializer
    filterset_fields = ['server', 'group', 'iam_user', 'group__iam_group']
    search_fields = [
        'uid', 'gid', 'username', 'description', 'directory', 'shell',
        'group__groupname',
    ]

    def get_queryset(self):
        return super().get_queryset().filter(
            iam_user__isnull=False,
        ).order_by('username')


class SystemGroupViewSet(ServerMultiDataViewSet):
    queryset = SystemGroup.objects.all()
    serializer_class = SystemGroupSerializer
    filterset_fields = ['server', 'iam_group']
    search_fields = ['gid', 'groupname']

    def get_queryset(self):
        return super().get_queryset().filter(
            iam_group__isnull=False,
        ).order_by('groupname')


class InterfaceViewSet(ServerMultiDataViewSet):
    queryset = Interface.objects.exclude(mac='00:00:00:00:00:00').order_by('name')
    serializer_class = InterfaceSerializer
    filterset_fields = ['server', 'type']
    search_fields = ['name', 'mac', 'address__address']


class SystemPackageViewSet(ServerMultiDataViewSet):
    queryset = SystemPackage.objects.order_by('name')
    serializer_class = SystemPackageSerializer
    filterset_fields = ['server', 'name', 'arch']
    search_fields = ['name', 'version', 'source', 'arch']


class PythonPackageViewSet(ServerMultiDataViewSet):
    queryset = PythonPackage.objects.order_by('name')
    serializer_class = PythonPackageSerializer
    filterset_fields = ['server', 'name']
    search_fields = ['name', 'version']
