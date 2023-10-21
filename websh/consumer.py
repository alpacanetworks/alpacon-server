import abc
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from termcolor import colored

from websh.models import UserChannel, PtyChannel

User = get_user_model()

logger = logging.getLogger(__name__)

WELCOME_MESSAGE = '''

 (`-')  _           _  (`-') (`-')  _                      <-. (`-')_ 
 (OO ).-/    <-.    \-.(OO ) (OO ).-/  _             .->      \( OO) )
 / ,---.   ,--. )   _.'    \ / ,---.   \-,-----.(`-')----. ,--./ ,--/ 
 | \ /`.\  |  (`-')(_...--'' | \ /`.\   |  .--./( OO).-.  '|   \ |  | 
 '-'|_.' | |  |OO )|  |_.' | '-'|_.' | /_) (`-')( _) | |  ||  . '|  |)
(|  .-.  |(|  '__ ||  .___.'(|  .-.  | ||  |OO ) \|  |)|  ||  |\    | 
 |  | |  | |     |'|  |      |  | |  |(_'  '--'\  '  '-'  '|  | \   | 
 `--' `--' `-----' `--'      `--' `--'   `-----'   `-----' `--'  `--' 

'''


class SessionConsumer(AsyncWebsocketConsumer):
    def get_remote_ip(self):
        if 'client' in self.scope:
            remote_ip = self.scope['client'][0]
        else:  # when testing, 'client' may not exist.
            remote_ip = '127.0.0.1'
        for header in self.scope['headers']:
            if header[0] == b'x-forwarded-for':
                remote_ip = header[1].decode('ascii').split(',')[0]
                break
        return remote_ip

    def get_user_agent(self):
        for header in self.scope['headers']:
            if header[0] == b'user-agent':
                return header[1].decode('ascii')
        return ''

    async def connect(self):
        self.channel_id = self.scope['url_route']['kwargs']['pk']
        self.token = self.scope['url_route']['kwargs']['token']

        try:
            self.channel = await self.get_channel()
        except ObjectDoesNotExist:
            return await self.close(code=404)

        try:
            self.session = await self.get_session()
        except ObjectDoesNotExist:
            return await self.close(code=404)

        self.channel.remote_ip = self.get_remote_ip()
        self.channel.opened_at = timezone.now()

        if self.channel_model == UserChannel:
            self.channel.user_agent = self.get_user_agent()

        if self.channel_model == PtyChannel:
            if self.channel.channel_name == '':
                self.channel.channel_name = self.channel_name.replace('sfic', 'specific')
        else:
            self.channel.channel_name = self.channel_name.replace('sfic', 'specific')

        await database_sync_to_async(
            self.channel.save
        )(update_fields=['channel_name', 'remote_ip', 'opened_at'])

        self.group_name = 'websh-%s' % self.session.id
        await self.channel_layer.group_add(
            self.group_name,
            # self.channel_name
            self.channel.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel.channel_name
            )
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'leave_message',
                    'message': 'exit'
                }
            )
        if hasattr(self, 'channel'):
            self.channel.closed_at = timezone.now()
            await database_sync_to_async(
                self.channel.save
            )(update_fields=['closed_at'])
        await super().disconnect(close_code)


class WebshConsumer(SessionConsumer):
    name = 'websh'
    channel_model = UserChannel

    @database_sync_to_async
    def get_channel(self):
        return self.channel_model.objects.select_related('session__server', 'session__user').get(id=self.channel_id)

    @database_sync_to_async
    def get_session(self):
        return self.channel.session

    @database_sync_to_async
    def get_pty_channel(self):
        try:
            pty_channel = PtyChannel.objects.get(session=self.session)
        except PtyChannel.DoesNotExist:
            pty_channel = PtyChannel.objects.create(session=self.session)

        return pty_channel

    async def connect(self):
        await super().connect()
        if not hasattr(self, 'session'):
            return

        await self.send(text_data=(
                'Please wait until ' + colored('[%s]' % self.session.server, 'green') + ' becomes connected...'
        ))

        pty_channel = await self.get_pty_channel()
        await database_sync_to_async(self.session.open_terminal)(pty_channel)

    async def receive(self, text_data=None, bytes_data=None):
        if not self.channel.read_only:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'user_message',
                    'message': text_data
                }
            )

    async def disconnect(self, close_code):
        # Only Master User can disconnect the websh connection
        if self.channel.is_master:
            try:
                if hasattr(self, 'session'):
                    self.session.closed_at = timezone.now()
                    logger.debug('%s left websh for %s.', self.session.user, self.session.server)
                    await database_sync_to_async(
                        self.session.save
                    )(
                        update_fields=['record', 'updated_at', 'closed_at']
                    )
            except Exception as e:
                logger.exception(e)
            await super().disconnect(close_code)

    async def pty_message(self, event):
        message = event['message']
        if hasattr(self, 'session'):
            self.session.record += event['message']
        await self.send(text_data=message)

    async def user_message(self, event):
        pass

    async def leave_message(self, event):
        url_prefix = settings.URL_PREFIX
        for header in self.scope['headers']:
            if header[0] == b'origin':
                url_prefix = header[1].decode()
                break
        if hasattr(self, 'session'):
            record_url = url_prefix + self.session.get_absolute_url()
            await self.send(text_data=(
                    '\r\nSession closed. Terminal became inactive.\r\n'
                    'Please ' + colored('reload', 'yellow')
                    + ' this page to open the terminal again.\r\n\r\n'
                # + 'Checkout '
                # + colored(record_url, 'cyan')
                # + ' for the websh history.'
            ))
        await self.close()


class PtyConsumer(SessionConsumer):
    channel_model = PtyChannel

    @database_sync_to_async
    def get_session(self):
        return self.channel.session

    @database_sync_to_async
    def get_channel(self):
        return self.channel_model.objects.select_related('session__server', 'session__user').get(id=self.channel_id)

    async def connect(self):
        await super().connect()
        if not hasattr(self, 'session'):
            return

        logger.debug('%s connected to the pty.', self.session.server)
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'pty_message',
                'message': WELCOME_MESSAGE
            }
        )
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'pty_message',
                'message': 'Websh for ' + colored('[%s]' % self.session.server, 'green') + ' became ready.\r\n'
            }
        )

    async def receive(self, text_data=None, bytes_data=None):
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'pty_message',
                'message': text_data
            }
        )

    async def user_message(self, event):
        message = event['message']
        await self.send(text_data=message)

    async def pty_message(self, event):
        pass

    async def leave_message(self, event):
        await self.close()
