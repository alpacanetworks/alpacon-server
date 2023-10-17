import json
import uuid
import logging
from datetime import timedelta

from django.db import models, transaction
from django.db.models import F, Q, Avg
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.urls import reverse
from django.utils.translation import gettext, gettext_lazy as _

# from packages.models import SystemPackage, PythonPackage
from wsutils.models import WebSocketClient
from events.models import Command
from utils.models import UUIDBaseModel


logger = logging.getLogger(__name__)


class Server(WebSocketClient):
    name = models.SlugField(
        max_length=16, unique=True,
        verbose_name=_('name'),
        help_text=_(
            'A name should only use letters, numbers, "_", and "-". '
            'No special characters or whitespaces allowed.'
        )
    )
    status = models.JSONField(_('status'), null=True)
    commissioned = models.BooleanField(_('commissioned'), default=False)
    version = models.CharField(_('version'), max_length=16, null=True, blank=True)
    osquery_version = models.CharField(max_length=16, null=True, blank=True)
    load = models.FloatField(_('load average (1m)'), null=True, editable=False)
    started_at = models.DateTimeField(_('started at'), null=True, editable=False)
    deleted_at = models.DateTimeField(_('deleted at'), null=True, editable=False)
    groups = models.ManyToManyField(
        'iam.Group',
        related_name='servers',
        related_query_name='server',
        verbose_name=_('groups'),
        help_text=_(
            '<ul><li>Select groups that are authorized to access this server.</li>'
            '<li>If you select alpacon group, all registered users will have access.</li>'
            '<li>This field cannot be blank.</li></ul>'
        )
    )

    _info = None
    _os_info = None
    _time = None
    _sys_users = None
    _sys_groups = None

    class Meta:
        verbose_name = _('server')
        verbose_name_plural = _('servers')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('servers:server:detail', args=(self.pk,))

    @property
    def system_info(self):
        if self._info is None:
            self._info = self.systeminfo_set.latest()
        return self._info

    @property
    def os_info(self):
        if self._os_info is None:
            self._os_info = self.osversion_set.latest()
        return self._os_info
    
    @property
    def time(self):
        if self._time is None:
            self._time = self.systemtime_set.latest()
        return self._time
    
    @property
    def sys_users(self):
        if self._sys_users is None:
            self._sys_users = self.systemuser_set.exclude(
                shell='/user/bin/false',
            ).order_by('uid')
        return self._sys_users

    @property
    def sys_groups(self):
        if self._sys_groups is None:
            self._sys_groups = self.systemgroup_set.order_by('gid')
        return self._sys_groups

    @property
    def platform(self):
        if self.os_info:
            return self.os_info.platform_like
        else:
            return None

    @property
    def cpu_physical_cores(self):
        return self.system_info.cpu_physical_cores
    
    @property
    def cpu_logical_cores(self):
        return self.system_info.cpu_logical_cores

    @property
    def cpu_type(self):
        return self.system_info.cpu_type

    @property
    def physical_memory(self):
        return self.system_info.physical_memory

    @property
    def os_name(self):
        return self.os_info.name

    @property
    def os_version(self):
        return self.os_info.version

    @property
    def boot_time(self):
        return self.time.boot_time

    @property
    def uptime(self):
        try:
            return (timezone.now() - self.time.boot_time).total_seconds()
        except:
            return None

    @property
    def groups_name(self):
        return self.groups.values_list('display_name', flat=True)

    def response_delay(self):
        result = self.command_set.filter(
            delivered_at__isnull=False,
            acked_at__isnull=False,
            delivered_at__gte=timezone.now()-timedelta(weeks=1),
        ).aggregate(
            delay_1h=Coalesce(Avg(
                (F('acked_at')-F('delivered_at')),
                filter=Q(delivered_at__gte=timezone.now()-timedelta(hours=1)),
            ), timedelta(0)),
            delay_1d=Coalesce(Avg(
                (F('acked_at')-F('delivered_at')),
                filter=Q(delivered_at__gte=timezone.now()-timedelta(days=1)),
            ), timedelta(0)),
            delay_1w=Coalesce(Avg(
                (F('acked_at')-F('delivered_at')),
            ), timedelta(0)),
        )
        for key in result:
            result[key] = result[key].total_seconds()
        last = self.command_set.filter(
            Q(delivered_at__isnull=False)
            & (
                Q(acked_at__isnull=False)
                | (Q(acked_at__isnull=True) & Q(delivered_at__lte=timezone.now()-timedelta(seconds=180)))
            )
        ).order_by('-scheduled_at').first()
        if last is None:
            result['delay_now'] = 0
        else:
            if last.acked_at is not None:
                delay = last.acked_at - last.delivered_at
            else:
                delay = timezone.now() - last.delivered_at
            result['delay_now'] = delay.total_seconds()
        return result

    def get_current_status(self):
        error = False
        warn = False
        messages = []
        if not self.is_connected:
            error = True
            messages.append('Server is not connected.')
        if not self.commissioned:
            error = True
            messages.append('Server information is not commissioned.')

        delay = self.response_delay()
        if delay['delay_now'] > 180:
            error = True
            messages.append('Response delay is over 3 minutes.')
        elif delay['delay_now'] > 15:
            warn = True
            messages.append('Response delay is over 15 seconds.')
        else:
            # Test system time only when response delay is okay to avoid measurement error.
            trecord = self.timerecord_set.order_by('-system_time').first()
            if trecord is not None:
                tdiff = trecord.diff
                if tdiff > 30:
                    if tdiff > 120:
                        error = True
                    else:
                        warn = True
                    messages.append('System time is not correct. (diff: %.1fs).' % tdiff)

        if not error and not warn:
            messages.append(gettext('Server is okay.'))
        if error:
            return {
                'code': 'error',
                'text': gettext('Error'),
                'icon': 'triangle-exclamation',
                'color': 'danger',
                'messages': messages,
                'meta': delay,
            }
        elif warn:
            return {
                'code': 'warn',
                'text': gettext('Warning'),
                'icon': 'circle-exclamation',
                'color': 'warning',
                'messages': messages,
                'meta': delay,
            }
        else:
            return {
                'code': 'ok',
                'text': gettext('Good'),
                'icon': 'circle-check',
                'color': 'success',
                'messages': messages,
                'meta': delay,
            }

    def get_latest_info(self):
        return self.systeminfo_set.latest()
    
    def get_latest_osinfo(self):
        return self.osversion_set.latest()

    def get_active_users(self):
        return self.systemuser_set.exclude(
            shell='/usr/bin/false'
        ).order_by('uid')

    def get_ip_interfaces(self):
        return self.interface_set.exclude(
            address__isnull=True,
        ).order_by('name')

    def execute(self, cmdline, shell='internal', data=None, requested_by=None, run_after=[]):
        if not self.enabled or self.deleted_at is not None:
            raise ValidationError(_('Invalid server.'))
        if data is not None and type(data) != str:
            data = json.dumps(data)
        cmd = Command(
            server=self,
            shell=shell,
            line=cmdline,
            data=data,
            requested_by=requested_by
        )
        if run_after:
            cmd.scheduled_at = timezone.now()
            with transaction.atomic():
                cmd.save()
                if type(run_after) == list:
                    cmd.run_after.add(*run_after)
                else:
                    cmd.run_after.add(run_after)
        elif self.is_connected:
            cmd.scheduled_at = cmd.delivered_at = timezone.now()
            cmd.save()
            cmd.execute(to_save=False)
        else:
            cmd.scheduled_at = timezone.now()
            cmd.save()
        return cmd

    def update_information(self, requested_by=None):
        logger.info('Sending commit request to %s.', self.name)
        return self.execute(
            shell='internal',
            cmdline='commit',
            requested_by=requested_by
        )

    def upgrade_system(self, requested_by=None):
        logger.info('Updating system for %s by %s.', self.name, requested_by)
        return self.execute(
            shell='internal',
            cmdline='update',
            requested_by=requested_by
        )

    def reboot_system(self, requested_by=None):
        logger.info('Rebooting system for %s by %s.', self.name, requested_by)
        return self.execute(
            shell='internal',
            cmdline='reboot',
            requested_by=requested_by
        )

    def shutdown_system(self, requested_by=None):
        logger.info('Shutdown system for %s by %s.', self.name, requested_by)
        return self.execute(
            shell='internal',
            cmdline='shutdown',
            requested_by=requested_by
        )

    def upgrade_agent(self, requested_by=None):
        logger.info('Sending upgrade server request to %s.', self)
        return self.execute(
            shell='internal',
            cmdline='upgrade',
            requested_by=requested_by
        )

    def restart_agent(self, requested_by=None):
        logger.info('Sending restart request to %s.', self)
        return self.execute(
            shell='internal',
            cmdline='restart',
            requested_by=requested_by
        )

    def shutdown_agent(self, requested_by=None):
        logger.info('Sending quit request to %s.', self)
        return self.execute(
            shell='internal',
            cmdline='quit',
            requested_by=requested_by
        )

    def has_user(self, user):
        return self.systemuser_set.filter(
            iam_user__pk=user.pk, 
        ).exists()

    def has_group(self, group):
        return self.systemgroup_set.filter(
            iam_group__pk=group.pk,
        ).exists()

    def add_user(self, user, gid, groupname, gids, requested_by=None, run_after=[]):
        return self.execute(
            shell='internal',
            cmdline='adduser %s' % user.username,
            data={
                'username': user.username,
                'uid': user.uid,
                'gid' : gid,
                'groups' : gids,
                'comment': '%s,,,,(alpacon)%s' % (user.get_full_name(), user.id),
                'home_directory': user.home_directory,
                'shell': user.shell,
                'groupname': groupname,
            },
            requested_by=requested_by,
            run_after=run_after,
        )

    def add_group(self, group, requested_by=None, run_after=[]):
        return self.execute(
            shell='internal',
            cmdline='addgroup %s' %  group.name,
            data={
                'groupname': group.name,
                'gid': group.gid,
            },
            requested_by=requested_by,
            run_after=run_after,
        )
    
    def del_user(self, user, requested_by=None, run_after=[]):
        return self.execute(
            shell='internal',
            cmdline='deluser %s' % user.username,
            data={
                'username': user.username,
            },
            requested_by=requested_by,
            run_after=run_after,
        )

    def del_group(self, group, requested_by=None, run_after=[]):
        return self.execute(
            shell='internal',
            cmdline='delgroup %s' % group.name,
            data={
                'groupname': group.name,
            },
            requested_by=requested_by,
            run_after=run_after,
        )

    # check and make group that the user is enrolled
    def prepare_user(self, user, group, deps):
        gids = []
        if self.platform == 'darwin':
            return

        for obj in user.membership_set.all():
            gids.append(obj.group.gid)

            if not self.has_group(obj.group):
                cmd = self.add_group(obj.group, requested_by=user)
                deps.append(cmd)

        if not self.has_user(user):
            cmd = self.add_user(
                user,
                group.gid,
                group.name,
                gids,
                requested_by=user,
                run_after=deps
            )
            deps.append(cmd)

        return deps


class Installer(models.Model):
    id = models.UUIDField(_('ID'), default=uuid.uuid4, primary_key=True)
    server = models.ForeignKey(
        'servers.Server', on_delete=models.CASCADE,
        verbose_name=_('server')
    )
    content = models.TextField(_('content'))
    hits = models.PositiveSmallIntegerField(verbose_name=_('hits'), default=0)
    added_at = models.DateTimeField(_('added_at'), auto_now_add=True)

    class Meta:
        verbose_name = _('installer')
        verbose_name_plural = _('installers')

    def get_absolute_url(self):
        return reverse('api:servers:installer-detail', kwargs={'pk': self.pk})


class Note(UUIDBaseModel):
    server = models.ForeignKey(
        'servers.Server', on_delete=models.CASCADE,
        verbose_name=_('server')
    )
    content = models.TextField(
        _('content'),
        max_length=512,
        help_text=_('Markdown is supported.')
    )
    private = models.BooleanField(
        _('private'),
        default=False,
        help_text=_('Private notes are visible only to you.')
    )
    pinned = models.BooleanField(
        _('pinned'),
        default=False,
        help_text=_('Pinned notes are listed first.')
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        editable=False,
        verbose_name=_('author')
    )

    class Meta:
        verbose_name = _('note')
        verbose_name_plural = _('notes')

    @property
    def author_name(self):
        return str(self.author)

    @property
    def server_name(self):
        return str(self.server)
