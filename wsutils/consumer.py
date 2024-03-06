import re
import logging

from asgiref.sync import sync_to_async

from django.db import transaction
from django.utils import timezone

from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from wsutils.models import WebSocketSession
from wsutils.tasks import drop_concurrent_sessions, delete_session


logger = logging.getLogger(__name__)

parser = re.compile('(\w+)[:=] ?"?([a-zA-Z0-9-_]+)"?')


class APIClientAsyncConsumer(AsyncJsonWebsocketConsumer):
    strict_ordering = True

    def get_remote_ip(self):
        if 'client' in self.scope:
            remote_ip = self.scope['client'][0]
        else: # when testing, 'client' may not exist.
            remote_ip = '127.0.0.1'
        for header in self.scope['headers']:
            if header[0] == b'x-forwarded-for':
                remote_ip = header[1].decode('ascii').split(',')[0]
                break
        return remote_ip

    @database_sync_to_async
    def create_session(self):
        self.session = WebSocketSession.objects.create(
            client=self.scope['wsclient'],
            remote_ip=self.get_remote_ip(),
            channel_id=self.channel_name
        )
        if not self.scope['wsclient'].concurrent:
            drop_concurrent_sessions.delay(self.scope['wsclient'].pk, self.session.pk)

    @database_sync_to_async
    def update_session(self):
        return WebSocketSession.objects.filter(
            pk=self.session.pk,
            deleted_at__isnull=True,
        ).update(
            updated_at=timezone.now()
        ) == 1

    @database_sync_to_async
    def delete_session(self):
        return WebSocketSession.objects.filter(
            pk=self.session.pk,
            deleted_at__isnull=True,
        ).update(
            deleted_at=timezone.now()
        ) == 1

    async def connect(self):
        if not self.scope['wsclient']:
            await self.close(code=403)
            return None
        else:
            await self.accept()
            await self.create_session()
            logger.debug('Connect for session %s (channel %s).', self.session.id, self.channel_name)
            return self.session

    async def receive_json(self, content):
        if not hasattr(self, 'session') or not await self.update_session():
            logger.debug('Can\'t identify the session.')
            return await self.close(code=400)
        return await super().receive_json(content)

    async def disconnect(self, close_code):
        if hasattr(self, 'session'):
            logger.debug('Disconnect for session %s (channel %s).', self.session.id, self.channel_name)
            await self.delete_session()

    async def send_message(self, text_data):
        content = text_data['content']
        await self.send_json(content)


class AuthedAsyncConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close(code=403)
            return False
        else:
            await self.accept()
            return True


class AuthedAsyncJsonConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close(code=403)
            return False
        else:
            await self.accept()
            return True
