import logging

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from utils.models import UUIDBaseModel
from api.apiclient.models import APIClient


logger = logging.getLogger(__name__)


class WebSocketClient(APIClient):
    _last_session = None

    class Meta:
        verbose_name = _('WebSocket client')
        verbose_name_plural = _('WebSocket clients')

    @property
    def is_connected(self) -> bool:
        return self.sessions.filter(deleted_at__isnull=True).exists()

    @property
    def last_session(self):
        if self._last_session is None:
            self._last_session = (
                self.sessions.filter(deleted_at__isnull=True).order_by('-updated_at').first()
                or self.sessions.order_by('-updated_at').first()
            )
        return self._last_session

    @property
    def remote_ip(self):
        try:
            return self.last_session.remote_ip
        except Exception as e:
            return None

    @property
    def last_connectivity(self):
        try:
            return self.last_session.updated_at
        except:
            return None

    def send(self, json_data):
        for session in self.sessions.filter(deleted_at__isnull=True):
            session.send(json_data)


class WebSocketSession(UUIDBaseModel):
    client = models.ForeignKey(
        WebSocketClient, on_delete=models.CASCADE,
        related_name='sessions',
        related_query_name='session',
        verbose_name=_('WebSocket client')
    )
    remote_ip = models.GenericIPAddressField(
        verbose_name=_('remote IP')
    )
    channel_id = models.CharField(
        max_length=128, editable=False,
        verbose_name=_('channel ID')
    )

    class Meta:
        verbose_name = _('WebSocket session')
        verbose_name_plural = ('WebSocket sessions')
        get_latest_by = 'updated_at'

    def __str__(self):
        return self.remote_ip

    def delete(self, *args, **kwargs):
        self.deleted_at = timezone.now()
        super().save(update_fields=['deleted_at'])

    def send(self, json_data):
        logger.debug('%s => %s', self.channel_id, json_data)
        async_to_sync(get_channel_layer().send)(self.channel_id, {
            'type': 'send_message',
            'content': json_data
        })

    def close(self, quit=False):
        if quit:
            self.send({
                'query': 'quit',
                'reason': 'New connection from the same host has been established.'
            })
        else:
            self.send({
                'query': 'reconnect',
                'reason': 'Session has retired. Please reconnect again to keep up to date.'
            })
        self.delete()
