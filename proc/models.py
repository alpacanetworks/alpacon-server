import uuid
from datetime import timedelta

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class TimestampedServerData(models.Model):
    id = models.UUIDField(_('ID'), default=uuid.uuid4, primary_key=True)
    server = models.ForeignKey(
        'servers.Server', on_delete=models.CASCADE,
        editable=False,
        verbose_name=_('server')
    )
    current = models.BooleanField(_('is current'), default=True)
    added_at = models.DateTimeField(_('added at'), auto_now_add=True)

    class Meta:
        abstract = True
        unique_together = ('server', 'added_at')
        get_latest_by = 'added_at'


class SystemInfo(TimestampedServerData):
    uuid = models.UUIDField(_('UUID'))
    cpu_type = models.CharField(_('CPU type'), max_length=32, blank=True, default='')
    cpu_subtype = models.CharField(_('CPU subtype'), max_length=32, blank=True, default='')
    cpu_brand = models.CharField(_('CPU brand'), max_length=64, blank=True, default='')
    cpu_physical_cores = models.IntegerField(_('CPU physical cores'))
    cpu_logical_cores = models.IntegerField(_('CPU logical cores'))
    physical_memory = models.BigIntegerField(_('physical memory'))
    hardware_vendor = models.CharField(_('hardware vendor'), max_length=128, blank=True, default='')
    hardware_model = models.CharField(_('hardware model'), max_length=128, blank=True, default='')
    hardware_version = models.CharField(_('hardware version'), max_length=128, blank=True, default='')
    hardware_serial = models.CharField(_('hardware serial'), max_length=128, blank=True, default='')
    computer_name = models.CharField(_('computer name'), max_length=128, blank=True, default='')
    hostname = models.CharField(_('hostname'), max_length=128, blank=True, default='')
    local_hostname = models.CharField(_('local hostname'), max_length=128, blank=True, default='')

    class Meta(TimestampedServerData.Meta):
        verbose_name = _('system information')
        verbose_name_plural = _('system information')

    def __str__(self):
        return self.computer_name


class OsVersion(TimestampedServerData):
    name = models.CharField(_('name'), max_length=32)
    version = models.CharField(_('version'), max_length=64)
    major = models.SmallIntegerField(_('major'), null=True, blank=True)
    minor = models.SmallIntegerField(_('minor'), null=True, blank=True)
    patch = models.SmallIntegerField(_('patch'), null=True, blank=True)
    build = models.CharField(_('build'), max_length=16, blank=True, default='')
    platform = models.CharField(_('platform'), max_length=16)
    platform_like = models.CharField(_('platform like'), max_length=16, blank=True)

    class Meta(TimestampedServerData.Meta):
        verbose_name = _('OS version')
        verbose_name_plural = _('OS versions')

    def __str__(self):
        return '%(name)s %(version)s' % {
            'name': self.name,
            'version': self.version,
        }


class SystemTime(TimestampedServerData):
    datetime = models.DateTimeField(_('datetime'))
    boot_time = models.DateTimeField(_('boot time'))
    timezone = models.CharField(_('local timezone'), max_length=16)
    uptime = models.PositiveBigIntegerField(_('uptime'))

    class Meta(TimestampedServerData.Meta):
        verbose_name = _('system time')
        verbose_name_plural = _('system times')

    def __str__(self):
        return '%(time)s' % {
            'time': self.datetime
        }

    def save(self, *args, **kwargs):
        if not self.boot_time:
            self.boot_time = self.datetime - timedelta(seconds=self.uptime)
        return super().save(*args, **kwargs)


class SystemUser(TimestampedServerData):
    uid = models.BigIntegerField(_('UID'))
    gid = models.BigIntegerField(_('GID'))
    username = models.CharField(_('username'), max_length=128)
    description = models.CharField(_('description'), max_length=128, blank=True, default='')
    directory = models.CharField(_('directory'), max_length=128, blank=True, default='')
    shell = models.CharField(_('shell'), max_length=32, blank=True, default='')
    group = models.ForeignKey(
        'proc.SystemGroup', on_delete=models.SET_NULL,
        null=True, editable=False,
        verbose_name=_('group')
    )
    iam_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, editable=False,
        verbose_name=_('IAM user')
    )

    class Meta(TimestampedServerData.Meta):
        verbose_name = _('system user')
        verbose_name_plural = _('system users')
        unique_together = ('server', 'uid', 'added_at')

    def __str__(self):
        return '%(username)s (%(uid)d)' % {
            'username': self.username,
            'uid': self.uid,
        }

    @property
    def iam_group(self):
        if self.group:
            return self.group.iam_group.id
        else:
            return None


class SystemGroup(TimestampedServerData):
    gid = models.BigIntegerField(_('GID'))
    groupname = models.CharField(_('groupname'), max_length=128)
    iam_group = models.ForeignKey(
        'iam.Group', on_delete=models.SET_NULL,
        null=True, editable=False,
        verbose_name=_('IAM group')
    )

    class Meta(TimestampedServerData.Meta):
        verbose_name = _('system group')
        verbose_name_plural = _('system groups')
        unique_together = ('server', 'gid', 'added_at')

    def __str__(self):
        return '%(groupname)s (%(gid)d)' % {
            'groupname': self.groupname,
            'gid': self.gid,
        }


class Interface(TimestampedServerData):
    IFF_UP = 1 << 0
    IFF_LOOPBACK = 1 << 3
    IFF_POINTOPOINT = 1 << 4
    IFF_RUNNING = 1 << 6

    name = models.CharField(_('name'), max_length=64)
    mac = models.CharField(_('MAC address'), max_length=20)
    type = models.PositiveIntegerField(_('type'))
    flags = models.PositiveIntegerField(_('flags'))
    mtu = models.PositiveIntegerField(_('MTU'), default=1500)
    link_speed = models.PositiveIntegerField(_('flags'), default=0)

    class Meta(TimestampedServerData.Meta):
        verbose_name = _('interface')
        verbose_name_plural = _('interfaces')
        unique_together = ('server', 'name', 'added_at')

    def __str__(self):
        return self.name

    @property
    def is_up(self):
        return bool(self.flags & self.IFF_UP)

    @property
    def is_running(self):
        return bool(self.flags & self.IFF_RUNNING)

    @property
    def is_loopback(self):
        return bool(self.flags & self.IFF_LOOPBACK)

    @property
    def is_p2p(self):
        return bool(self.flags & self.IFF_POINTOPOINT)


class InterfaceAddress(models.Model):
    id = models.UUIDField(_('ID'), default=uuid.uuid4, primary_key=True)
    interface = models.ForeignKey(
        Interface, on_delete=models.CASCADE,
        related_name='addresses',
        related_query_name='address',
        verbose_name=_('interface')
    )
    address = models.GenericIPAddressField(_('address'))
    mask = models.GenericIPAddressField(_('mask'))
    broadcast = models.GenericIPAddressField(_('broadcast'), null=True, blank=True)

    class Meta:
        verbose_name = _('interface address')
        verbose_name_plural = _('interface addresses')
        unique_together = ('interface', 'address')

    def __str__(self):
        return self.address


class PythonVersion(TimestampedServerData):
    python2 = models.CharField(_('python2'), max_length=32, null=True, blank=True)
    python3 = models.CharField(_('python3'), max_length=32, null=True, blank=True)

    class Meta(TimestampedServerData.Meta):
        verbose_name = _('python version')
        verbose_name_plural = _('python versions')


class SystemPackage(TimestampedServerData):
    name = models.CharField(_('name'), max_length=128)
    version = models.CharField(_('version'), max_length=128)
    source = models.CharField(_('source'), max_length=512, blank=True, null=True)
    arch = models.CharField(_('arch'), max_length=16, blank=True, null=True)

    class Meta(TimestampedServerData.Meta):
        verbose_name = _('system package')
        verbose_name_plural = _('system packages')
        unique_together = ('server', 'name', 'added_at')

    def __str__(self):
        return '%s-%s' % (self.name, self.version)

    def uninstall(self, requested_by):
        return self.server.execute(
            cmdline='package uninstall %s' % self.name,
            requested_by=requested_by
        )


class PythonPackage(TimestampedServerData):
    name = models.CharField(_('name'), max_length=128)
    version = models.CharField(_('version'), max_length=64)

    class Meta(TimestampedServerData.Meta):
        verbose_name = _('python package')
        verbose_name_plural = _('python packages')
        unique_together = ('server', 'name', 'added_at')

    def __str__(self):
        return '%s-%s' % (self.name, self.version)

    def uninstall(self, requested_by):
        self.server.execute(
            cmdline='pypackage uninstall %s' % self.name,
            requested_by=requested_by
        )
