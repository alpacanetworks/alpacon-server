from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async

from wsutils.auth import APIAuthMiddlewareStack
from wsutils.models import WebSocketClient
from wsutils.consumer import APIClientAsyncConsumer, AuthedAsyncConsumer


APIClientTestApp = APIAuthMiddlewareStack(APIClientAsyncConsumer.as_asgi())
UserTestApp = APIAuthMiddlewareStack(AuthedAsyncConsumer.as_asgi())
User = get_user_model()


class WebSocketClientModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        client1 = WebSocketClient.objects.create(owner=self.user)
        client2 = WebSocketClient.objects.create(owner=self.user)
        self.id1 = client1.id
        self.id2 = client2.id

        self.key1 = client1.make_random_key()
        client1.set_key(self.key1)
        client1.save()
        self.key2 = client2.make_random_key()
        client2.set_key(self.key2)
        client2.save()

    def test_make_random_key(self):
        key = WebSocketClient.make_random_key()
        self.assertEqual(len(key), 32)
        key = WebSocketClient.make_random_key(length=64)
        self.assertEqual(len(key), 64)
        key = WebSocketClient.make_random_key(length=16, allowed_chars='a')
        self.assertEqual(key, 'a'*16)

    def test_client_check_key(self):
        client1 = WebSocketClient.objects.get(id=self.id1)
        client2 = WebSocketClient.objects.get(id=self.id2)

        self.assertTrue(client1.check_key(self.key1))
        self.assertTrue(client2.check_key(self.key2))
        self.assertFalse(client1.check_key(self.key2))
        self.assertFalse(client2.check_key(self.key1))
        self.assertFalse(client1.check_key(None))
        self.assertFalse(client1.check_key(''))

    def test_unset_key(self):
        client = WebSocketClient.objects.create(owner=self.user)

        # test client without key set
        self.assertFalse(client.check_key(None))
        self.assertFalse(client.check_key(''))
        self.assertFalse(client.check_key('\n'))

        # test client with unusable key
        client.set_unusable_key()
        client.save()
        self.assertFalse(client.check_key(None))
        self.assertFalse(client.check_key(''))
        self.assertFalse(client.check_key('\n'))

    def test_is_connected(self):
        client = WebSocketClient.objects.create(owner=self.user)
        client.sessions.create(
            remote_ip='127.0.0.1',
            channel_id='fake_channel1'
        )
        self.assertTrue(client.is_connected)
        client.sessions.update(deleted_at=timezone.now())
        self.assertFalse(client.is_connected)
        client.sessions.create(
            remote_ip='127.0.0.2',
            channel_id='fake_channel2'
        )
        client.sessions.all().delete()
        self.assertFalse(client.is_connected)

    def test_remote_ip(self):
        client = WebSocketClient.objects.create(owner=self.user)
        client.sessions.create(
            remote_ip='127.0.0.1',
            channel_id='fake_channel'
        )
        self.assertEqual(client.remote_ip, '127.0.0.1')
        client._last_session = None # to avoid cache side effect
        client.sessions.create(
            remote_ip='127.0.0.2',
            channel_id='fake_channel'
        )
        self.assertEqual(client.remote_ip, '127.0.0.2')

    def test_unusable_key(self):
        client = WebSocketClient.objects.create(owner=self.user)
        client.set_key(client.make_random_key())
        client.save()
        self.assertTrue(client.has_usable_key())

        client.set_unusable_key()
        client.save()
        self.assertFalse(client.has_usable_key())

    def test_create_api_client(self):
        """
        `create_api_client` should return proper client object and key.
        """
        (client, key) = WebSocketClient.objects.create_api_client(self.user)
        self.assertTrue(client.check_key(key))
        self.assertFalse(client.check_key(None))
        self.assertFalse(client.check_key(''))

    def test_get_valid_client(self):
        """
        `get_valid_client` should return correct client object
        """
        (client, key) = WebSocketClient.objects.create_api_client(self.user)
        obj = WebSocketClient.objects.get_valid_client(id=client.id, key=key)
        self.assertEqual(client.id, obj.id)


class APIAuthTestCase(TransactionTestCase):
    def setUp(self):
        self.username = get_random_string(16)
        self.password = get_random_string(16)
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
        )
        self.token = self.user.apitoken_set.create()
        (self.wsclient, self.key) = WebSocketClient.objects.create_api_client(owner=self.user)

    async def test_session_auth(self):
        await sync_to_async(self.client.login)(username=self.username, password=self.password)
        communicator = WebsocketCommunicator(
            UserTestApp,
            'ws/test/',
            headers=(
                (b'cookie', ('sessionid=%s' % self.client.session.session_key).encode('ascii')),
            )
        )
        (connected, _) = await communicator.connect()
        self.assertTrue(connected)

    async def test_apitoken_auth(self):
        communicator = WebsocketCommunicator(
            UserTestApp,
            'ws/test/',
            headers=(
                (b'authorization', ('token="%s"' % self.token.key).encode('ascii')),
            )
        )
        (connected, _) = await communicator.connect()
        self.assertTrue(connected)

    async def test_apiclient_auth(self):
        communicator = WebsocketCommunicator(
            APIClientTestApp,
            'ws/test/',
            headers=(
                (b'authorization', ('id="%s", key="%s"' % (self.wsclient.id, self.key)).encode('ascii')),
            )
        )

        # connection test
        (connected, _) = await communicator.connect()
        self.assertTrue(connected)

    async def test_no_auth(self):
        communicator = WebsocketCommunicator(
            UserTestApp,
            'ws/test/',
        )
        (connected, _) = await communicator.connect()
        self.assertFalse(connected)


class WebSocketConsumerTestCase(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        (self.client, self.key) = WebSocketClient.objects.create_api_client(owner=self.user)

    async def test_consumer(self):
        communicator = WebsocketCommunicator(
            APIClientTestApp,
            'ws/test/',
            headers=(
                (b'authorization', ('id="%s", key="%s"' % (self.client.id, self.key)).encode('ascii')),
            )
        )

        # connection test
        (connected, _) = await communicator.connect()
        self.assertTrue(connected)
        count = await database_sync_to_async(self.client.sessions.count)()
        self.assertEqual(count, 1)

        # send/recv test
        await communicator.send_json_to({'message': 'ping'})
        await sync_to_async(self.client.send)(json_data={'message': 'pong'})
        response = await communicator.receive_json_from()
        self.assertTrue('message' in response)
        self.assertEqual(response['message'], 'pong')

        # send/recv test again
        await communicator.send_json_to({'message': 'ping2'})
        await sync_to_async(self.client.send)(json_data={'message': 'pong2'})
        response = await communicator.receive_json_from()
        self.assertTrue('message' in response)
        self.assertEqual(response['message'], 'pong2')

        # disconnect
        await communicator.disconnect()

    async def test_session_revocation(self):
        communicator = WebsocketCommunicator(
            APIClientTestApp,
            'ws/test/',
            headers=(
                (b'authorization', ('id="%s", key="%s"' % (self.client.id, self.key)).encode('ascii')),
            )
        )
        (connected, _) = await communicator.connect()
        self.assertTrue(connected)
        (count, _) = await database_sync_to_async(self.client.sessions.all().delete)()
        self.assertEqual(count, 1)
        await communicator.send_json_to({'message': 'hello'})
        await communicator.receive_nothing()
        await communicator.disconnect()

    async def test_no_credentials(self):
        communicator = WebsocketCommunicator(
            APIClientTestApp,
            'ws/test/',
        )

        # connection test - should be denied
        (connected, _) = await communicator.connect()
        self.assertFalse(connected)
        count = await database_sync_to_async(self.client.sessions.count)()
        self.assertEqual(count, 0)

        # send/recv test
        await communicator.send_json_to({'message': 'ping'})
        await sync_to_async(self.client.send)(json_data={'message': 'pong'})
        await communicator.receive_nothing()
