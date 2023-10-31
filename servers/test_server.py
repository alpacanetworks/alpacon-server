from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model

from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from channels.db import database_sync_to_async

from wsutils.auth import APIAuthMiddlewareStack
from servers.models import *
from servers.routing import websocket_urlpatterns

from api.apiclient.tokens import JWTRefreshToken


User = get_user_model()
WsApp = APIAuthMiddlewareStack(
    URLRouter(websocket_urlpatterns)
)


class ServerModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')

    def test_create_server(self):
        server = Server.objects.create(name='testing', owner=self.user)
        server.set_key(server.make_random_key())
        server.save()


class ServerAPIViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')


class BackhaulConsumerTestCase(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.server = Server.objects.create(name='testing', owner=self.user)
        self.key = self.server.make_random_key()
        self.server.set_key(self.key)
        self.server.save()
        self.assertTrue(self.server.check_key(self.key))

    async def test_connect(self):
        communicator = WebsocketCommunicator(
            WsApp,
            'ws/servers/backhaul/',
            headers=(
                (b'Authorization', ('id="%s", key="%s"' % (self.server.id, self.key)).encode('ascii')),
            )
        )

        # connection test
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        count = await database_sync_to_async(self.server.sessions.count)()
        self.assertEqual(count, 1)

        response = await communicator.receive_json_from()
        self.assertTrue('query' in response)
        self.assertEqual(response['query'], 'commit')

        # disconnect
        await communicator.disconnect()

    async def test_no_credentials(self):
        communicator = WebsocketCommunicator(
            WsApp,
            'ws/servers/backhaul/',
        )

        # connection test - should be denied
        connected, subprotocol = await communicator.connect()
        self.assertFalse(connected)
        count = await database_sync_to_async(self.server.sessions.count)()
        self.assertEqual(count, 0)

        response = await communicator.receive_json_from()
        self.assertTrue('query' in response)
        self.assertEqual(response['query'], 'quit')

        self.assertTrue('reason' in response)
        self.assertEqual(response['reason'], 'Permission denied. Please check your id and key again.')

        await communicator.disconnect()

class JWTTestCase(TransactionTestCase):
    """
    When requesting a websocket connection, Test whether it works normally when an access token is entered in the header.
    """
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.server = Server.objects.create(name='testing', owner=self.user)
        self.key = self.server.make_random_key()
        self.server.set_key(self.key)
        self.server.save()
        self.assertTrue(self.server.check_key(self.key))
        self.refresh = JWTRefreshToken.for_client(self.server.id)
        self.access = self.refresh.access_token


    async def test_connect(self):
        communicator = WebsocketCommunicator(
            WsApp,
            'ws/servers/backhaul/',
            headers=(
                (b'Authorization', f'Bearer {self.access}'.encode('ascii')),
            )
        )

        # connection test
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        count = await database_sync_to_async(self.server.sessions.count)()
        self.assertEqual(count, 1)

        response = await communicator.receive_json_from()
        self.assertTrue('query' in response)
        self.assertEqual(response['query'], 'commit')

        # disconnect
        await communicator.disconnect()

    async def test_no_credentials(self):
        communicator = WebsocketCommunicator(
            WsApp,
            'ws/servers/backhaul/',
        )

        # connection test - should be denied
        connected, subprotocol = await communicator.connect()
        self.assertFalse(connected)
        count = await database_sync_to_async(self.server.sessions.count)()
        self.assertEqual(count, 0)

        response = await communicator.receive_json_from()
        self.assertTrue('query' in response)
        self.assertEqual(response['query'], 'quit')

        self.assertTrue('reason' in response)
        self.assertEqual(response['reason'], 'Permission denied. Please check your id and key again.')

        await communicator.disconnect() 

    async def test_invalid_token(self):
        refresh = JWTRefreshToken.for_client(self.server.id)
        access = refresh.access_token
        access.set_exp(lifetime=-timedelta(seconds=1))

        communicator = WebsocketCommunicator(
            WsApp,
            'ws/servers/backhaul/',
            headers=(
                (b'Authorization', f'Bearer {access}'.encode('ascii')),
            )
        )

        # connection test - should be denied
        connected, subprotocol = await communicator.connect()
        self.assertFalse(connected)
        count = await database_sync_to_async(self.server.sessions.count)()
        self.assertEqual(count, 0)

        response = await communicator.receive_json_from()
        self.assertTrue('query' in response)
        self.assertEqual(response['query'], 'quit')

        self.assertTrue('reason' in response)
        self.assertEqual(response['reason'], 'Permission denied. Please check your id and key again.')

        await communicator.disconnect() 

class WebsocketReconnectTestCase(TransactionTestCase):
    """
    When the connection is lost after connecting to a Websocket with an access token, it tests whether the websocket can be reconnected with a new access token.
    """

    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.server = Server.objects.create(name='testing', owner=self.user)
        self.key = self.server.make_random_key()
        self.server.set_key(self.key)
        self.server.save()
        self.assertTrue(self.server.check_key(self.key))
        self.refresh = JWTRefreshToken.for_client(self.server.id)
        self.access = self.refresh.access_token

    async def test_reconnect(self):

        # connection test 1
        communicator = WebsocketCommunicator(
            WsApp,
            'ws/servers/backhaul/',
            headers=(
                (b'Authorization', f'Bearer {self.access}'.encode('ascii')),
            )
        )

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        count = await database_sync_to_async(self.server.sessions.count)()
        self.assertEqual(count, 1)
            
        response = await communicator.receive_json_from()
        self.assertTrue('query' in response)
        self.assertEqual(response['query'], 'commit')

        #Jwtrefreshveiw connect
        response = self.client.post(
            reverse('api:apiclient:jwt:refresh'), {
                "refresh": str(self.refresh)
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue('access' in response.data)
        self.new_access = response.data['access']

        # disconnect 1
        await communicator.disconnect()

        # Reconnection test 2
        communicator = WebsocketCommunicator(
            WsApp,
            'ws/servers/backhaul/',
            headers=(
                (b'Authorization', f'Bearer {self.new_access}'.encode('ascii')),
            )
        )

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        count = await database_sync_to_async(self.server.sessions.count)()
        self.assertEqual(count, 2)

        response = await communicator.receive_json_from()
        self.assertTrue('query' in response)
        self.assertEqual(response['query'], 'commit')

        # disconnect 2
        await communicator.disconnect()