import os
import json
import logging
from datetime import timedelta

from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _

from events.models import Command
from utils.models import UUIDBaseModel
from iam.models import Group, User


logger = logging.getLogger(__name__)


# This model represents a WebSocket Session, not an HTTP Session
class Session(UUIDBaseModel):
    rows = models.PositiveSmallIntegerField(_('terminal rows'), default=0)
    cols = models.PositiveSmallIntegerField(_('terminal cols'), default=0)

    record = models.TextField(_('record'), default='')

    server = models.ForeignKey(
        'servers.Server', on_delete=models.CASCADE,
        related_name='websh_sessions',
        related_query_name='websh_session',
        verbose_name=_('server')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, editable=False,
        verbose_name=_('user')
    )
    username = models.CharField(_('username'), blank=True, max_length=128)
    groupname = models.CharField(_('groupname'), default='alpacon', blank=True, max_length=128)

    closed_at = models.DateTimeField(_('closed_at'), null=True, editable=False)

    _user_channel = None

    class Meta:
        verbose_name = _('session')
        verbose_name_plural = _('sessions')

    def __str__(self):
        return '%(server)s-%(date)s by %(user)s' % {
            'server': self.server,
            'date': self.added_at,
            'user': self.user,
        }

    def get_absolute_url(self):
        return reverse('api:websh:session-detail', kwargs={'pk': self.pk})

    def get_shared_url(self):
        return settings.REACT_URL + '/websh/join?session=%s' % self.pk

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    @property
    def user_agent(self):
        if self._user_channel is None:
            self._user_channel = self.userchannel_set.order_by('-opened_at').first()
        return self._user_channel.user_agent if self._user_channel else None

    @property
    def remote_ip(self):
        if self._user_channel is None:
            self._user_channel = self.userchannel_set.order_by('-opened_at').first()
        return self._user_channel.remote_ip if self._user_channel else None

    @property
    def user_name(self):
        return str(self.user)

    @property
    def server_name(self):
        return str(self.server)

    def open_terminal(self, pty_channel):
        deps = []
        group = Group.get_default()

        # Call prepare_user only if it's the user's own account
        if self.user.username == self.username:
            self.server.prepare_user(self.user, group, deps)

        pty_websocket_url = pty_channel.get_server_ws_url()

        data = {
            'session_id': str(self.id),
            'url': pty_websocket_url,
            'rows': self.rows,
            'cols': self.cols,
        }

        data['username'] = self.username
        data['groupname'] = self.groupname
        # Due to macOS not supporting adduser
        if self.server.platform == 'darwin':
            data['home_directory'] = self.user.home_directory
        else:
            data['home_directory'] = self.server.systemuser_home_directory(self.username)

        self.server.execute(
            shell='internal',
            cmdline='openpty',
            data=data,
            requested_by=self.user,
            run_after=deps,
        )

    def resize_terminal(self):
        self.server.execute(
            cmdline='resizepty',
            shell='internal',
            data={
                'session_id': str(self.pk),
                'rows': self.rows,
                'cols': self.cols,
            },
            requested_by=self.user,
        )


class Channel(UUIDBaseModel):
    CHANNEL_TOKEN_LENGTH = 32

    session = models.ForeignKey(
        'websh.session', on_delete=models.CASCADE,
        null=True, editable=False,
        verbose_name=_('session')
    )
    token = models.CharField(_('token'), null=True, editable=False, max_length=CHANNEL_TOKEN_LENGTH)
    channel_name = models.CharField(_('channel name'), max_length=128, default='', editable=False)
    remote_ip = models.GenericIPAddressField(verbose_name=_('remote IP address'), null=True, editable=False)
    opened_at = models.DateTimeField(_('opened at'), null=True, editable=False)
    closed_at = models.DateTimeField(_('closed_at'), null=True, editable=False)

    token_created_at = models.DateTimeField(_('token created at'), null=True, editable=False)
    token_expired_at = models.DateTimeField(_('token expired at'), null=True, editable=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.token is None:
            self.token = get_random_string(self.CHANNEL_TOKEN_LENGTH)
            self.token_created_at = timezone.now()
            self.token_expired_at = self.token_created_at + settings.WEBSH_SESSION_SHARE_TIMEOUT

        super().save(*args, **kwargs)

    def is_token_valid(self):
        return self.token_expired_at > timezone.now()

    def get_user_ws_url(self):
        return settings.URL_ROOT + 'ws/websh/%(channel_id)s/%(token)s/' % {
            'channel_id': self.id,
            'token': self.token,
        }

    def get_server_ws_url(self):
        return settings.URL_ROOT + 'ws/websh/pty/%(channel_id)s/%(token)s/' % {
            'channel_id': self.id,
            'token': self.token,
        }


class UserChannel(Channel):
    USER_CHANNEL_PASSWORD_LENGTH = 16

    user_agent = models.CharField(
        _('user agent'), max_length=256,
        default='', editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, editable=False,
        verbose_name=_('user')
    )
    password = models.CharField(_('password'), null=True, editable=False, max_length=USER_CHANNEL_PASSWORD_LENGTH)
    is_master = models.BooleanField(_('is master'), blank=False, default=False)
    read_only = models.BooleanField(_('read only'), blank=False, default=False)

    class Meta:
        verbose_name = _('user channel')
        verbose_name_plural = _('user channels')

    def save(self, *args, **kwargs):
        if self.password is None:
            self.password = get_random_string(self.USER_CHANNEL_PASSWORD_LENGTH)
        super().save(*args, **kwargs)

    def is_password_valid(self, password):
        return self.password == password


class PtyChannel(Channel):
    class Meta:
        verbose_name = _('pty channel')
        verbose_name_plural = _('pty channels')


class AbstractFile(UUIDBaseModel):
    name = models.CharField(_('name'), max_length=128, editable=False)
    path = models.CharField(
        _('path'),
        max_length=512,
        blank=True, default='',
        help_text=_(
            'Specify the path for this file. '
            'If this field is left blank, your home directory will be used as default.'
        )
    )
    content = models.FileField(_('content'), upload_to='websh/files/')
    server = models.ForeignKey(
        'servers.Server', on_delete=models.CASCADE,
        verbose_name=_('server')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        editable=False,
        verbose_name=_('user')
    )
    username = models.CharField(_('username'), blank=True, max_length=128)
    groupname = models.CharField(_('groupname'), default='alpacon', blank=True, max_length=128)
    command = models.ForeignKey(
        'events.Command',
        blank=True, null=True, on_delete=models.CASCADE,
        verbose_name=_('command'),
    )
    expires_at = models.DateTimeField(_('expires at'), blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.content.name
        if self.expires_at is None:
            self.expires_at = timezone.now() + timedelta(days=1)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.content.delete()
        super().delete(*args, **kwargs)

    @property
    def size(self):
        try:
            return self.content.size
        except:
            return None


class UploadedFile(AbstractFile):
    class Meta:
        verbose_name = _('uploaded file')
        verbose_name_plural = _('uploaded files')

    def get_absolute_url(self):
        return reverse('api:websh:uploadedfile-detail', kwargs={'pk': self.pk})

    def get_download_url(self):
        return settings.URL_PREFIX + reverse(
            'api:websh:uploadedfile-download', kwargs={'pk': self.pk}
        )

    def upload(self, run_after=[]):
        deps = []
        group = Group.get_default()

        if os.path.split(self.path)[1] != '':
            path = self.path
        elif self.path:
            path = os.path.join(self.path, self.name)
        else:
            if self.server.platform in ['debian', 'rhel']:
                path = os.path.join(self.server.systemuser_home_directory(self.username), self.name)
            elif self.server.platform == 'darwin':
                path = os.path.join(self.user.home_directory.replace('/home', '/Users'), self.name)
            else:
                path = self.name

        # Call prepare_user only if it's the user's own account
        if self.user.username == self.username:
            self.server.prepare_user(self.user, group, deps)

        logger.info('Sending file "%s" to %s. (username: %s, groupname: %s)', self.name, path, self.username, self.groupname)
        self.command = self.server.execute(
            'download "%s"' % path,
            data=json.dumps({
                'type': 'url',
                'content': self.get_download_url(),
                'username': self.username,
                'groupname': self.groupname,
            }),
            username=self.username,
            groupname=self.groupname,
            requested_by=self.user,
            run_after=deps,
        )
        self.save()

        return self.command


class DownloadedFile(AbstractFile):
    class Meta:
        verbose_name = _('downloaded file')
        verbose_name_plural = _('downloaded files')

    def get_absolute_url(self):
        return reverse('api:websh:downloadedfile-detail', kwargs={'pk': self.pk})

    def get_upload_url(self):
        return settings.URL_PREFIX + reverse(
            'api:websh:downloadedfile-upload', kwargs={'pk': self.pk}
        )

    def get_download_url(self):
        return settings.URL_PREFIX + reverse(
            'api:websh:downloadedfile-download', kwargs={'pk': self.pk}
        )

    def download(self, run_after=[]):
        deps = []
        group = Group.get_default()

        logger.info('Sending upload_url to %s. (username: %s, groupname: %s) ', self.server.name, self.username, self.groupname)

        # Call prepare_user only if it's the user's own account
        if self.user.username == self.username:
            self.server.prepare_user(self.user, group, deps)

        self.command = self.server.execute(
            'upload "%s"' % self.path,
            data=json.dumps({
                'type': 'url',
                'content': self.get_upload_url(),
                'username': self.username,
                'groupname': self.groupname,
            }),
            requested_by=self.user,
            run_after=deps,
        )
        self.save()

        return self.command
