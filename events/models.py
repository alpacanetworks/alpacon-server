import re
import json
import logging
from datetime import timedelta

from django.db import models, transaction
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from utils.models import UUIDBaseModel
from history.models import RequestStat


logger = logging.getLogger(__name__)


class Event(UUIDBaseModel):
    server = models.ForeignKey(
        'servers.Server', on_delete=models.CASCADE,
        editable=False,
        verbose_name=_('server')
    )
    count = models.PositiveIntegerField(_('count'), default=1)
    record = models.CharField(_('record'), max_length=128)
    reporter = models.CharField(_('reporter'), max_length=128)
    description = models.TextField(_('description'), null=True, blank=True)
    data = models.JSONField(_('data'), null=True, blank=True)

    class Meta:
        verbose_name = _('event')
        verbose_name_plural = _('events')
        get_latest_by = 'updated_at'

    def __str__(self):
        return '[%(server)s] %(record)s' % {
            'server': self.server.name,
            'record': self.record,
        }

    def handle_event(self):
        if self.reporter == 'alpamon' and self.record == 'started':
            self.server.started_at = timezone.now()
            self.server.save(update_fields=['started_at', 'updated_at'])
            self.server.installer_set.all().delete()
        elif self.reporter == 'alpamon' and self.record == 'committed':
            # match = re.match(r'Committed system information\. version\: (?P<version>[a-zA-Z0-9._-]+), osquery\: (?P<osquery>[a-zA-Z0-9._-]+)', self.description)
            # if match:
            #     self.server.version = match.group('version')
            #     self.server.osquery_version = match.group('osquery')
            self.server.commissioned = True
            self.server.save(update_fields=['commissioned', 'updated_at'])


class Command(UUIDBaseModel):
    SHELLS = (
        ('system', _('System')),
        ('osquery', _('Osquery')),
        ('internal', _('Internal')),
    )
    server = models.ForeignKey(
        'servers.Server', on_delete=models.CASCADE,
        verbose_name=_('server')
    )
    shell = models.CharField(
        _('shell'),
        max_length=8,
        choices=SHELLS, default='system'
    )
    line = models.CharField(
        _('command line'),
        max_length=512,
        help_text=_('Should avoid using commands that might need standard input.')
    )
    data = models.TextField(_('data'), null=True, blank=True)
    success = models.BooleanField(_('success'), null=True, blank=True)
    result = models.TextField(_('result'), null=True, blank=True)
    elapsed_time = models.FloatField(_('elapsed time'), null=True)
    scheduled_at = models.DateTimeField(
        _('scheduled at'),
        default=timezone.now, blank=True,
        help_text=_('Executed now if left blank.')
    )
    delivered_at = models.DateTimeField(_('delivered at'), null=True, editable=False)
    acked_at = models.DateTimeField(_('acked at'), null=True, blank=True)
    handled_at = models.DateTimeField(_('handled at'), null=True, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, editable=False,
        verbose_name=_('requested by')
    )
    username = models.CharField(_('username'), blank=True, max_length=128)
    groupname = models.CharField(_('groupname'), default='alpacon', blank=True, max_length=128)
    run_after = models.ManyToManyField(
        'events.Command',
        related_name='run_before',
        blank=True,
        verbose_name=_('run after'),
        help_text=_('Execute this command after running prior commands.')
    )

    class Meta:
        verbose_name = _('command')
        verbose_name_plural = _('commands')
        get_latest_by = 'added_at'

    def __str__(self):
        return '%s %s> %s' % (self.server, self.shell, self.line)

    def get_absolute_url(self):
        return reverse('api:events:command-detail', kwargs={'pk': self.pk})

    def has_perm(self, user, permission_required='r'):
        if permission_required == 'r':
            return True
        else:
            if self.acked_at is None:
                return True
            else:
                return False

    @property
    def response_delay(self):
        if self.acked_at is not None and self.delivered_at is not None:
            secs = (self.acked_at - self.delivered_at).total_seconds()
            return secs if secs > 0 else 0
        else:
            return None

    @property
    def server_name(self):
        return str(self.server)

    @property
    def requested_by_name(self):
        return str(self.requested_by)

    @property
    def status(self):
        if self.handled_at is not None:
            if self.success:
                return {
                    'text': _('Success'),
                    'color': 'success',
                    'cancellable': False,
                    'message': _('Finished at %(time)s.') % {'time': self.handled_at.astimezone(tz=timezone.get_current_timezone())},
                }
            else:
                return {
                    'text': _('Failed'),
                    'color': 'danger',
                    'cancellable': False,
                    'message': _('Failed at %(time)s.') % {'time': self.handled_at.astimezone(tz=timezone.get_current_timezone())},
                }
        elif self.acked_at is not None:
            if self.acked_at < timezone.now() - timedelta(seconds=10*60):
                return {
                    'text': _('Stuck'),
                    'color': 'danger',
                    'cancellable': False,
                    'message': _('Command started to run, but got no result.')
                }
            else:
                return {
                    'text': _('Acked'),
                    'color': 'warning',
                    'cancellable': False,
                    'message': _('Command is being executed on the server.')
                }
        elif self.delivered_at is not None:
            if self.delivered_at < timezone.now() - timedelta(seconds=10*60):
                return {
                    'text': _('Stuck'),
                    'color': 'danger',
                    'cancellable': False,
                    'message': _('Sent command to server, but got no response.')
                }
            else:
                return {
                    'text': _('Sent'),
                    'color': 'warning',
                    'cancellable': False,
                    'message': _('Sent command to server, waiting response.')
                }
        elif self.scheduled_at is not None:
            if self.scheduled_at < timezone.now():
                return {
                    'text': _('Queued'),
                    'color': 'warning',
                    'cancellable': True,
                    'message': _('Command is on due, waiting for delivery.')
                }
            else:
                return {
                    'text': _('Scheduled'),
                    'color': 'secondary',
                    'cancellable': True,
                    'message': _('Command will be sent if the scheduled time arrives.')
                }
        else:
            return {
                'text': _('Error'),
                'color': 'danger',
                'cancellable': True,
                'message': _('Error: Not implemented state.')
            }

    def execute(self, to_save=True):
        command = {
            'id': str(self.id),
            'shell': self.shell,
            'line': self.line,
            'user': self.username,
            'group': self.groupname,
        }
        if self.data:
            command['data'] = self.data

        self.server.send({
            'query': 'command',
            'command': command,
        })
        logger.info(
            'Sent command request to %s by %s (%s> %s)',
            self.server, self.requested_by, self.shell, self.line
        )
        if to_save:
            self.delivered_at = timezone.now()
            super().save(update_fields=['delivered_at'])

    @classmethod
    def execute_all_scheduled(cls, server_pk=None):
        commands = cls.objects.select_for_update(of=('self',)).filter(
            server__enabled=True,
            server__deleted_at__isnull=True,
            scheduled_at__lte=timezone.now(),
            delivered_at__isnull=True,
            handled_at__isnull=True,
        )
        if server_pk is not None:
            commands = commands.filter(server__pk=server_pk)
        count = 0
        with transaction.atomic():
            for command in commands:
                if (
                    not command.run_after.filter(handled_at__isnull=True).exists()
                    and command.server.is_connected
                ):
                    command.execute()
                    count += 1
        return count

    def retry(self):
        self.scheduled_at = None
        self.delivered_at = None
        self.acked_at = None
        self.handled_at = None
        super().save(update_fields=['scheduled_at', 'delivered_at', 'acked_at', 'handled_at'])

    def ack(self):
        self.acked_at = timezone.now()
        super().save(update_fields=['acked_at'])

    def fin(self, success, result):
        from events.tasks import execute_scheduled_commands
        from servers.tasks import check_server_status

        if self.handled_at is not None:
            return

        self.success = success
        self.result = result
        self.handled_at = timezone.now()
        if not success:
            self.run_before.filter(handled_at__isnull=True).update(
                success=False,
                result='Cancelled due to prior commmand failure.',
                handled_at=self.handled_at,
            )
        super().save(update_fields=['success', 'result', 'handled_at'])

        if self.shell == 'internal' and self.line == 'ping' and success and self.requested_by is None:
            self.server.timerecord_set.create(system_time=result)

        elif self.shell == 'internal' and self.line == 'debug' and success and self.requested_by is None:
            try:
                data = json.loads(result)
                self.server.debugrecord_set.create(
                    content=data,
                )
                for i in range(len(data['reporters'])):
                    stats = data['reporters'][i]
                    prev = self.server.requeststat_set.filter(
                        index=i,
                    ).order_by('-date').first()
                    cur = RequestStat(
                        server=self.server,
                        index=i,
                        date=self.handled_at,
                        cum_success=stats['success'],
                        cum_failure=stats['failure'],
                        cum_ignored=stats['ignored'],
                        delay=stats['delay'],
                        latency=stats['latency'],
                    )
                    if prev and prev.date > self.server.started_at:
                        cur.success = cur.cum_success - prev.cum_success
                        cur.failure = cur.cum_failure - prev.cum_failure
                        cur.ignored = cur.cum_ignored - prev.cum_ignored
                    else:
                        cur.success = cur.cum_success
                        cur.failure = cur.cum_failure
                        cur.ignored = cur.cum_ignored
                    cur.save()

            except Exception as e:
                logger.exception(e)

        if self.run_before.filter(handled_at__isnull=True).exists():
            execute_scheduled_commands.delay(self.server.pk)
        
        check_server_status.delay(self.server.pk)
