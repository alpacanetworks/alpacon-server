from datetime import timedelta

from asgiref.sync import sync_to_async
from termcolor import colored

from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.test import TransactionTestCase

from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from proc.models import SystemUser, SystemGroup
from servers.models import Server
from iam.models import Group
from iam.test_user import get_random_username
from websh.models import Session, UserChannel, PtyChannel
from websh.routing import websocket_urlpatterns
from wsutils.auth import APIAuthMiddlewareStack


User = get_user_model()
WsApp = APIAuthMiddlewareStack(
    URLRouter(websocket_urlpatterns)
)

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


class SessionTestCase(APITestCase):
    def setUp(self):
        self.username = get_random_username()
        self.password = get_random_string(16)
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            is_staff=True,
            is_superuser=True,
        )

        self.server = Server.objects.create(name='testing', owner=self.user, commissioned=True)
        self.server.osversion_set.create(
            name='ubuntu',
            version='22.04',
            platform='debian',
            platform_like='debian',
        )
        self.server.sessions.create(
            remote_ip='127.0.0.1',
            channel_id='fake_channel1'
        )
        self.client.login(username=self.username, password=self.password)

        # Generally, system users and groups on this server are synchronized with alpacon.
        # The 'root' is neither an IAM user nor part of an IAM group, thus 'iam_user' and 'iam_group' are not defined for it.
        SystemUser.objects.create(server=self.server, uid=2010, gid=2000, username='root')
        SystemGroup.objects.create(server=self.server, gid=2000, groupname='root')

    def test_create_session(self):
        response = self.client.post(
            reverse('api:websh:session-list'), {
                'server': self.server.pk,
                'username': 'root',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        session_count = Session.objects.count()
        self.assertEqual(session_count, 1)

        channel_count = UserChannel.objects.count()
        self.assertEqual(channel_count, 1)

        user_channel = UserChannel.objects.first()

        # Token Validation Test
        self.assertAlmostEqual(user_channel.token_created_at, timezone.now(), delta=timedelta(seconds=1))
        self.assertEqual(user_channel.token_expired_at, user_channel.token_created_at + timedelta(minutes=30))
        self.assertTrue(user_channel.token_expired_at > timezone.now())

        # is_master Field Test
        self.assertTrue(user_channel.is_master)



class SessionPermissionTestCase(APITestCase):
    def setUp(self):
        self.password = get_random_string(16)
        self.owner = User.objects.create_user(
            username='owner',
            password=self.password,
        )
        self.user = User.objects.create_user(
            username='user',
            password=self.password,
        )
        self.staff = User.objects.create_user(
            username='staff',
            password=self.password,
            is_staff=True,
        )
        self.superuser = User.objects.create_user(
            username='superuser',
            password=self.password,
            is_staff=True,
            is_superuser=True,
        )
        self.group_member = User.objects.create_user(
            username='group-member',
            password=self.password,
        )
        self.group_manager = User.objects.create_user(
            username='group-manager',
            password=self.password,
        )
        self.group_owner = User.objects.create_user(
            username='group-owner',
            password=self.password,
        )
        self.group = Group.objects.create(
            name='group',
            display_name='Group',
        )
        self.group.membership_set.create(user=self.group_member, role='member')
        self.group.membership_set.create(user=self.group_manager, role='manager')
        self.group.membership_set.create(user=self.group_owner, role='owner')

        self.server = Server.objects.create(name='testing', owner=self.owner, commissioned=True)
        self.server.sessions.create(
            remote_ip='127.0.0.1',
            channel_id='fake_channel1'
        )
        self.server.groups.add(self.group)

        # Generally, system users and groups on this server are synchronized with alpacon.
        # The 'root' is neither an IAM user nor part of an IAM group, thus 'iam_user' and 'iam_group' are not defined for it.
        SystemUser.objects.create(server=self.server, uid=2010, gid=2000, username='root')
        SystemGroup.objects.create(server=self.server, gid=2000, groupname='root')


    def test_create_session_owner(self):
        self.client.login(username='owner', password=self.password)
        response = self.client.post(
            reverse('api:websh:session-list'), {
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = Session.objects.get(pk=response.data['id'])
        self.assertEqual(session.username, 'owner')
        self.assertEqual(session.groupname, 'alpacon') # For non-system users, ensure groupname is 'alpacon'.

        response = self.client.post(
            reverse('api:websh:session-list'), {
                'server': self.server.pk,
                'username': 'root',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = Session.objects.get(pk=response.data['id'])
        self.assertEqual(session.username, 'root')
        self.assertEqual(session.groupname, 'root') # Check if system user's groupname matches username.


    def test_create_session_user(self):
        self.client.login(username='user', password=self.password)
        response = self.client.post(
            reverse('api:websh:session-list'), {
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Below-staff cannot create sessions for others
        response = self.client.post(
            reverse('api:websh:session-list'), {
                'server': self.server.pk,
                'username': 'root',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_session_staff(self):
        self.client.login(username='staff', password=self.password)
        response = self.client.post(
            reverse('api:websh:session-list'), {
                'server': self.server.pk,
                'username': self.staff.username,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = Session.objects.get(pk=response.data['id'])
        self.assertEqual(session.username, self.staff.username)
        self.assertEqual(session.groupname, 'alpacon')

        # Staff-level or higher users can create session for other accounts
        response = self.client.post(
            reverse('api:websh:session-list'), {
                'server': self.server.pk,
                'username': 'root',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = Session.objects.get(pk=response.data['id'])
        self.assertEqual(session.username, 'root')
        self.assertEqual(session.groupname, 'root') # if systemuser groupname is same at username

        response = self.client.post(
            reverse('api:websh:session-list'), {
                'server': self.server.pk,
                'username': 'superuser',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_create_session_superuser(self):
        self.client.login(username='superuser', password=self.password)
        response = self.client.post(
            reverse('api:websh:session-list'), {
                'server': self.server.pk,
                'username': self.superuser.username,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = Session.objects.get(pk=response.data['id'])
        self.assertEqual(session.username, self.superuser.username)
        self.assertEqual(session.groupname, 'alpacon') # if iam user (not systemuser) groupname is set alpacon

        response = self.client.post(
            reverse('api:websh:session-list'), {
                'server': self.server.pk,
                'username': 'root',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = Session.objects.get(pk=response.data['id'])
        self.assertEqual(session.username, 'root')
        self.assertEqual(session.groupname, 'root')

    def test_create_session_group_member(self):
        self.client.login(username='group-member', password=self.password)
        response = self.client.post(
            reverse('api:websh:session-list'), {
                'server': self.server.pk,
                'username': self.group_member.username,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = Session.objects.get(pk=response.data['id'])
        self.assertEqual(session.username, self.group_member.username)
        self.assertEqual(session.groupname, 'alpacon')

        response = self.client.post(
            reverse('api:websh:session-list'), {
                'server': self.server.pk,
                'username': 'root',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_session_group_manager(self):
        self.client.login(username='group-manager', password=self.password)
        response = self.client.post(
            reverse('api:websh:session-list'), {
                'server': self.server.pk,
                'username': self.group_manager.username,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = Session.objects.get(pk=response.data['id'])
        self.assertEqual(session.username, self.group_manager.username)
        self.assertEqual(session.groupname, 'alpacon')

        response = self.client.post(
            reverse('api:websh:session-list'), {
                'server': self.server.pk,
                'username': 'root',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = Session.objects.get(pk=response.data['id'])
        self.assertEqual(session.username, 'root')
        self.assertEqual(session.groupname, 'root')

    def test_create_session_group_owner(self):
        self.client.login(username='group-owner', password=self.password)
        response = self.client.post(
            reverse('api:websh:session-list'), {
                'server': self.server.pk,
                'username': self.group_owner.username,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = Session.objects.get(pk=response.data['id'])
        self.assertEqual(session.username, self.group_owner.username)
        self.assertEqual(session.groupname, 'alpacon')

        response = self.client.post(
            reverse('api:websh:session-list'), {
                'server': self.server.pk,
                'username': 'root',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = Session.objects.get(pk=response.data['id'])
        self.assertEqual(session.username, 'root')
        self.assertEqual(session.groupname, 'root')


    # Prevents creation of sessions with usernames or groupnames not registered in IAM or Proc, even for users with staff-level permissions or higher.
    def test_command_creation_with_unregistered_user_group(self):
        self.client.login(username='superuser', password=self.password)
        response = self.client.post(
            reverse('api:websh:session-list'), {
                'server': self.server.pk,
                'username': 'unregistered',  # Use 'unregistered' to indicate absence in IAM/Proc
                'groupname': 'unregistered',  # Use 'unregistered' to indicate absence in IAM/Proc
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ConsumerTestCase(TransactionTestCase):

    def setUp(self):
        self.username = get_random_username()
        self.password = get_random_string(16)
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            is_staff=True,
            is_superuser=True,
        )

        self.server = Server.objects.create(name='testing', owner=self.user, commissioned=True)
        self.server.osversion_set.create(
            name='ubuntu',
            version='22.04',
            platform='debian',
            platform_like='debian',
        )
        self.server.sessions.create(
            remote_ip='127.0.0.1',
            channel_id='fake_channel1'
        )
        self.client.login(username=self.username, password=self.password)
        self.session = Session.objects.create(
            server=self.server,
            user=self.user,
            username='root',
        )
        self.user_channel = UserChannel.objects.create(
            session=self.session,
            user=self.user,
            is_master=True,
        )
        # Generally, system users and groups on this server are synchronized with alpacon.
        # The 'root' is neither an IAM user nor part of an IAM group, thus 'iam_user' and 'iam_group' are not defined for it.
        SystemUser.objects.create(server=self.server, uid=2010, gid=2000, username='root')
        SystemGroup.objects.create(server=self.server, gid=2000, groupname='root')

    async def test_connect(self):
        user_communicator = WebsocketCommunicator(
            WsApp,
            'ws/websh/{}/{}/'.format(self.user_channel.id, self.user_channel.token),
        )

        connected, _ = await user_communicator.connect()
        self.assertTrue(connected)

        response = await user_communicator.receive_from()
        self.assertEqual(response, 'Please wait until ' + colored('[%s]' % self.session.server,
                                                                  'green') + ' becomes connected...')

        self.pty_channel = await sync_to_async(PtyChannel.objects.first)()

        pty_websocket_url = self.pty_channel.get_server_ws_url()

        pty_communicator = WebsocketCommunicator(
            WsApp,
            pty_websocket_url
        )

        connected, _ = await pty_communicator.connect()
        self.assertTrue(connected)

        response = await user_communicator.receive_from()
        self.assertEqual(response, WELCOME_MESSAGE)

        response = await user_communicator.receive_from()
        self.assertEqual(response, 'Websh for ' + colored('[%s]' % self.session.server, 'green') + ' became ready.\r\n')

        await user_communicator.send_to('ls')
        response = await pty_communicator.receive_from()
        self.assertEqual(response, 'ls')

        await pty_communicator.send_to('ls')
        response = await user_communicator.receive_from()
        self.assertEqual(response, 'ls')

        await user_communicator.disconnect()
        await pty_communicator.disconnect()


class SessionShareTestCase(APITestCase):
    def setUp(self):
        self.password = get_random_string(16)
        self.usernames = ['master', get_random_username(), get_random_username()]
        self.users = []
        self.clients = []

        for username in self.usernames:
            user = User.objects.create_user(username=username, password=self.password)
            self.users.append(user)

            client = APIClient()
            client.login(username=username, password=self.password)
            self.clients.append(client)

        # Add a user to the Alpacon Server who hasn't logged in
        user_without_login = User.objects.create_user(username='no_login_user', password=self.password)
        self.users.append(user_without_login)

        client_without_login = APIClient()
        self.clients.append(client_without_login)

        self.master_user, self.user1, self.user2, self.no_login_user = self.users
        self.master_client, self.client1, self.client2, self.no_login_client = self.clients

        self.server = Server.objects.create(name='testing', owner=self.master_user, commissioned=True)
        self.server.sessions.create(
            remote_ip='127.0.0.1',
            channel_id='fake_channel1'
        )
        self.session = Session.objects.create(
            server=self.server,
            user=self.master_user,
            username='root',
        )
        self.master_user_channel = UserChannel.objects.create(
            session=self.session,
            user=self.master_user,
            is_master=True,
        )
        # Generally, system users and groups on this server are synchronized with alpacon.
        # The 'root' is neither an IAM user nor part of an IAM group, thus 'iam_user' and 'iam_group' are not defined for it.
        SystemUser.objects.create(server=self.server, uid=2010, gid=2000, username='root')
        SystemGroup.objects.create(server=self.server, gid=2000, groupname='root')
    def test_share_session(self):
        share_response = self.master_client.post(
            reverse('api:websh:session-share', kwargs={'pk': self.session.id}),
            data={
                'server': self.server.pk,
                'read_only': False,
            }
        )
        self.assertEqual(share_response.status_code, status.HTTP_201_CREATED)

        # share_channel is a channel created by the share action with no user assigned.
        share_channel = UserChannel.objects.get(user=None, session_id=self.session.id)

        shared_response = self.client1.post(
            reverse('api:websh:session-join', kwargs={'pk': self.session.id}),
            data={
                'password': share_channel.password
            }
        )
        self.assertEqual(shared_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(UserChannel.objects.filter(user=self.user1, is_master=False).exists())

    def test_share_session_with_no_login_user(self):
        share_response = self.master_client.post(
            reverse('api:websh:session-share', kwargs={'pk': self.session.id}),
            data={
                'server': self.server.pk,
                'read_only': False,
            }
        )
        self.assertEqual(share_response.status_code, status.HTTP_201_CREATED)

        # share_channel is a channel created by the share action with no user assigned.
        share_channel = UserChannel.objects.get(user=None, session_id=self.session.id)

        shared_response = self.no_login_client.post(
            reverse('api:websh:session-join', kwargs={'pk': self.session.id}),
            data={
                'password': share_channel.password
            }
        )
        self.assertEqual(shared_response.status_code, status.HTTP_201_CREATED)
        # Do not store User information in UserChannel when the user is not authenticated.
        self.assertFalse(UserChannel.objects.filter(user=self.no_login_user).exists())


    def test_token_expiration(self):
        share_response = self.master_client.post(
            reverse('api:websh:session-share', kwargs={'pk': self.session.id}),
            data={
                'server': self.server.pk,
                'read_only': False,
            }
        )
        self.assertEqual(share_response.status_code, status.HTTP_201_CREATED)

        # share_channel is a channel created by the share action with no user assigned.
        # share_channel's user information is updated when the shared URL is accessed by the shared user.
        share_channel = UserChannel.objects.get(user=None, session_id=self.session.id)

        # to indicate the expiration of the token's validity period
        share_channel.token_created_at -= timedelta(minutes=100)
        share_channel.token_expired_at -= timedelta(minutes=100)
        share_channel.save()

        shared_response = self.client1.post(
            reverse('api:websh:session-join', kwargs={'pk': self.session.id}),
            data={
                'password': share_response.data['password']
            }
        )
        self.assertEqual(shared_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_password(self):
        share_response = self.master_client.post(
            reverse('api:websh:session-share', kwargs={'pk': self.session.id}),
            data={
                'server': self.server.pk,
                'read_only': False,
            }
        )
        self.assertEqual(share_response.status_code, status.HTTP_201_CREATED)\

        shared_response = self.client1.post(
            reverse('api:websh:session-join', kwargs={'pk': self.session.id}),
            data={
                'password': None
            }
        )
        self.assertEqual(shared_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(str(shared_response.data['password'][0]), "This field may not be null.")

    def test_invalid_password(self):
        share_response = self.master_client.post(
            reverse('api:websh:session-share', kwargs={'pk': self.session.id}),
            data={
                'server': self.server.pk,
                'read_only': False,
            }
        )
        self.assertEqual(share_response.status_code, status.HTTP_201_CREATED)

        shared_response = self.client1.post(
            reverse('api:websh:session-join', kwargs={'pk': self.session.id}),
            data={
                'password': 'test'
            }
        )
        self.assertEqual(shared_response.status_code, status.HTTP_400_BAD_REQUEST)


class ConsumerShareTestCase(TransactionTestCase):

    def setUp(self):
        self.password = get_random_string(16)
        self.usernames = ['master', get_random_username(), get_random_username(), get_random_username()]
        self.users = []
        self.clients = []

        for username in self.usernames:
            user = User.objects.create_user(username=username, password=self.password)
            self.users.append(user)

            client = APIClient()
            client.login(username=username, password=self.password)
            self.clients.append(client)

        self.master_user, self.user1, self.user2, self.user3 = self.users
        self.master_client, self.client1, self.client2, self.client3 = self.clients

        self.server = Server.objects.create(name='testing', owner=self.master_user, commissioned=True)
        self.server.osversion_set.create(
            name='ubuntu',
            version='22.04',
            platform='debian',
            platform_like='debian',
        )
        self.server.sessions.create(
            remote_ip='127.0.0.1',
            channel_id='fake_channel1'
        )

        # Generally, system users and groups on this server are synchronized with alpacon.
        # The 'root' is neither an IAM user nor part of an IAM group, thus 'iam_user' and 'iam_group' are not defined for it.
        SystemUser.objects.create(server=self.server, uid=2010, gid=2000, username='root')
        SystemGroup.objects.create(server=self.server, gid=2000, groupname='root')

        self.session = Session.objects.create(
            server=self.server,
            user=self.master_user,
            username='root',
        )

        self.master_user_channel = UserChannel.objects.create(
            session=self.session,
            user=self.master_user,
            is_master=True,
        )

        self.user1_channel = UserChannel.objects.create(
            session=self.session,
            user=self.user1,
            is_master=False,
            read_only=False,
        )

        self.user2_channel = UserChannel.objects.create(
            session=self.session,
            user=self.user2,
            is_master=False,
            read_only=False,
        )

        # user3 has the only_read field set to True, meaning that user3 cannot send messages.
        self.user3_channel = UserChannel.objects.create(
            session=self.session,
            token=get_random_string(32),
            user=self.user2,
            is_master=False,
            read_only=True,
        )

    async def test_share_connect(self):
        # The master user first performs the websh connection.
        master_user_communicator = WebsocketCommunicator(
            WsApp,
            'ws/websh/{}/{}/'.format(self.master_user_channel.id, self.master_user_channel.token),
        )

        connected, _ = await master_user_communicator.connect()
        self.assertTrue(connected)

        response = await master_user_communicator.receive_from()
        self.assertEqual(response, 'Please wait until ' + colored('[%s]' % self.session.server,
                                                                  'green') + ' becomes connected...')

        self.pty_channel = await sync_to_async(PtyChannel.objects.first)()

        pty_websocket_url = self.pty_channel.get_server_ws_url()

        pty_communicator = WebsocketCommunicator(
            WsApp,
            pty_websocket_url
        )

        connected, _ = await pty_communicator.connect()
        self.assertTrue(connected)

        response = await master_user_communicator.receive_from()
        self.assertEqual(response, WELCOME_MESSAGE)

        response = await master_user_communicator.receive_from()
        self.assertEqual(response, 'Websh for ' + colored('[%s]' % self.session.server, 'green') + ' became ready.\r\n')

        # The master user shares the shared URL after connecting to websh, allowing multiple users to connect to the shell.
        user1_communicator = WebsocketCommunicator(
            WsApp,
            'ws/websh/{}/{}/'.format(self.user1_channel.id, self.user1_channel.token),
        )

        connected, _ = await user1_communicator.connect()
        self.assertTrue(connected)

        response = await user1_communicator.receive_from()
        self.assertEqual(response, 'Please wait until ' + colored('[%s]' % self.session.server,
                                                                  'green') + ' becomes connected...')

        user2_communicator = WebsocketCommunicator(
            WsApp,
            'ws/websh/{}/{}/'.format(self.user2_channel.id, self.user2_channel.token),
        )

        connected, _ = await user2_communicator.connect()
        self.assertTrue(connected)

        response = await user2_communicator.receive_from()
        self.assertEqual(response, 'Please wait until ' + colored('[%s]' % self.session.server,
                                                                  'green') + ' becomes connected...')

        # When the master user enters a message.
        await master_user_communicator.send_to('alpacon')
        response = await pty_communicator.receive_from()
        self.assertEqual(response, 'alpacon')

        # Other users cannot receive messages until ptyChannel sends one.
        self.assertTrue(await user1_communicator.receive_nothing(timeout=1))
        self.assertTrue(await user2_communicator.receive_nothing(timeout=1))

        # ptyChannel broadcasts the message.
        await pty_communicator.send_to('alpacon')

        response = await master_user_communicator.receive_from()
        self.assertEqual(response, 'alpacon')

        response = await user1_communicator.receive_from()
        self.assertEqual(response, 'alpacon')

        response = await user2_communicator.receive_from()
        self.assertEqual(response, 'alpacon')

        # When the shared user enters a message.
        await user2_communicator.send_to('alpamon')
        response = await pty_communicator.receive_from()
        self.assertEqual(response, 'alpamon')

        # Other users cannot receive messages until ptyChannel sends one.
        self.assertTrue(await user1_communicator.receive_nothing(timeout=1))
        self.assertTrue(await user2_communicator.receive_nothing(timeout=1))

        # ptyChannel broadcasts the message.
        await pty_communicator.send_to('alpamon')

        response = await user2_communicator.receive_from()
        self.assertEqual(response, 'alpamon')

        response = await master_user_communicator.receive_from()
        self.assertEqual(response, 'alpamon')

        response = await user1_communicator.receive_from()
        self.assertEqual(response, 'alpamon')

        await master_user_communicator.disconnect()
        await user1_communicator.disconnect()
        await user2_communicator.disconnect()

        await pty_communicator.disconnect()

    async def test_master_disconnect(self):
        # The master user first performs the websh connection.
        master_user_communicator = WebsocketCommunicator(
            WsApp,
            'ws/websh/{}/{}/'.format(self.master_user_channel.id, self.master_user_channel.token),
        )

        connected, _ = await master_user_communicator.connect()
        self.assertTrue(connected)

        response = await master_user_communicator.receive_from()
        self.assertEqual(response, 'Please wait until ' + colored('[%s]' % self.session.server,
                                                                  'green') + ' becomes connected...')

        self.pty_channel = await sync_to_async(PtyChannel.objects.first)()

        pty_websocket_url = self.pty_channel.get_server_ws_url()

        pty_communicator = WebsocketCommunicator(
            WsApp,
            pty_websocket_url
        )

        connected, _ = await pty_communicator.connect()
        self.assertTrue(connected)

        response = await master_user_communicator.receive_from()
        self.assertEqual(response, WELCOME_MESSAGE)

        response = await master_user_communicator.receive_from()
        self.assertEqual(response, 'Websh for ' + colored('[%s]' % self.session.server, 'green') + ' became ready.\r\n')

        user1_communicator = WebsocketCommunicator(
            WsApp,
            'ws/websh/{}/{}/'.format(self.user1_channel.id, self.user1_channel.token),
        )

        connected, _ = await user1_communicator.connect()
        self.assertTrue(connected)

        response = await user1_communicator.receive_from()
        self.assertEqual(response, 'Please wait until ' + colored('[%s]' % self.session.server,
                                                                  'green') + ' becomes connected...')

        # The master user disconnects the websh connection.
        await master_user_communicator.disconnect()
        self.assertTrue(await master_user_communicator.receive_nothing(timeout=3))

        # Check if the shared users' websh connections are also disconnected.
        response = await user1_communicator.receive_from()
        self.assertEqual(response, '\r\nSession closed. Terminal became inactive.\r\n'
                                   'Please ' + colored('reload', 'yellow')
                         + ' this page to open the terminal again.\r\n\r\n')

    async def test_user_disconnect(self):
        # The master user first performs the websh connection.
        master_user_communicator = WebsocketCommunicator(
            WsApp,
            'ws/websh/{}/{}/'.format(self.master_user_channel.id, self.master_user_channel.token),
        )

        connected, _ = await master_user_communicator.connect()
        self.assertTrue(connected)

        response = await master_user_communicator.receive_from()
        self.assertEqual(response, 'Please wait until ' + colored('[%s]' % self.session.server,
                                                                  'green') + ' becomes connected...')

        self.pty_channel = await sync_to_async(PtyChannel.objects.first)()

        pty_websocket_url = self.pty_channel.get_server_ws_url()

        pty_communicator = WebsocketCommunicator(
            WsApp,
            pty_websocket_url
        )

        connected, _ = await pty_communicator.connect()
        self.assertTrue(connected)

        response = await master_user_communicator.receive_from()
        self.assertEqual(response, WELCOME_MESSAGE)

        response = await master_user_communicator.receive_from()
        self.assertEqual(response, 'Websh for ' + colored('[%s]' % self.session.server, 'green') + ' became ready.\r\n')

        user1_communicator = WebsocketCommunicator(
            WsApp,
            'ws/websh/{}/{}/'.format(self.user1_channel.id, self.user1_channel.token),
        )

        connected, _ = await user1_communicator.connect()
        self.assertTrue(connected)

        response = await user1_communicator.receive_from()
        self.assertEqual(response, 'Please wait until ' + colored('[%s]' % self.session.server,
                                                                  'green') + ' becomes connected...')

        user2_communicator = WebsocketCommunicator(
            WsApp,
            'ws/websh/{}/{}/'.format(self.user2_channel.id, self.user2_channel.token),
        )

        connected, _ = await user2_communicator.connect()
        self.assertTrue(connected)

        response = await user2_communicator.receive_from()
        self.assertEqual(response, 'Please wait until ' + colored('[%s]' % self.session.server,
                                                                  'green') + ' becomes connected...')

        # Shared users' websh disconnect does not terminate the existing shared session.
        await user1_communicator.disconnect()

        # Master user and other Shared users maintain websh connection while using the shell terminal.
        await master_user_communicator.send_to('alpacon')
        response = await pty_communicator.receive_from()
        self.assertEqual(response, 'alpacon')

        await pty_communicator.send_to('alpacon')

        response = await master_user_communicator.receive_from()
        self.assertEqual(response, 'alpacon')

        response = await user2_communicator.receive_from()
        self.assertEqual(response, 'alpacon')

    async def test_only_read(self):
        # The master user first performs the websh connection.
        master_user_communicator = WebsocketCommunicator(
            WsApp,
            'ws/websh/{}/{}/'.format(self.master_user_channel.id, self.master_user_channel.token),
        )

        connected, _ = await master_user_communicator.connect()
        self.assertTrue(connected)

        response = await master_user_communicator.receive_from()
        self.assertEqual(response, 'Please wait until ' + colored('[%s]' % self.session.server,
                                                                  'green') + ' becomes connected...')

        self.pty_channel = await sync_to_async(PtyChannel.objects.first)()

        pty_websocket_url = self.pty_channel.get_server_ws_url()

        pty_communicator = WebsocketCommunicator(
            WsApp,
            pty_websocket_url
        )

        connected, _ = await pty_communicator.connect()
        self.assertTrue(connected)

        response = await master_user_communicator.receive_from()
        self.assertEqual(response, WELCOME_MESSAGE)

        response = await master_user_communicator.receive_from()
        self.assertEqual(response, 'Websh for ' + colored('[%s]' % self.session.server, 'green') + ' became ready.\r\n')

        user3_communicator = WebsocketCommunicator(
            WsApp,
            'ws/websh/{}/{}/'.format(self.user3_channel.id, self.user3_channel.token),
        )

        connected, _ = await user3_communicator.connect()
        self.assertTrue(connected)

        response = await user3_communicator.receive_from()
        self.assertEqual(response, 'Please wait until ' + colored('[%s]' % self.session.server,
                                                                  'green') + ' becomes connected...')

        # user3 has the only_read field set to True, meaning that user3 cannot send messages.
        await user3_communicator.send_to('alpacon')
        self.assertTrue(await pty_communicator.receive_nothing(timeout=3))