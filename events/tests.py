from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from rest_framework import status

from rest_framework.test import APITestCase

from events.models import Command
from iam.models import Group
from iam.test_user import get_random_username
from proc.models import SystemGroup, SystemUser
from servers.models import Server

User = get_user_model()

class CommandTestCase(APITestCase):
    def setUp(self):
        self.username = get_random_username()
        self.password = get_random_string(16)
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
        )
        self.group = Group.objects.create(
            name=get_random_username(),
            display_name=get_random_string(128),
        )
        self.group.membership_set.create(user=self.user, role='owner')
        self.server = Server.objects.create(name='testing', owner=self.user, commissioned=True)

        self.server.osversion_set.create(
            name='ubuntu',
            version='22.04',
            platform='debian',
            platform_like='debian',
        )
        self.server.groups.add(self.group)
        self.client.login(username=self.username, password=self.password)
        self.server.sessions.create(
            remote_ip='127.0.0.1',
            channel_id='fake_channel1'
        )

    def test_create_command(self):
        response = self.client.post(
            reverse('api:events:command-list'), {
                'shell': 'system',
                'line': 'pwd',
                'username': self.username,
                'groupname': self.group.name,
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_command_with_no_user_groupname(self):
        response = self.client.post(
            reverse('api:events:command-list'), {
                'shell': 'system',
                'line': 'pwd',
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cmd = Command.objects.get(pk=response.data['id'])
        self.assertEqual(cmd.username, self.username)
        self.assertEqual(cmd.groupname, 'alpacon')  # For non-system users, ensure groupname is 'alpacon'.

    # Test command creation with a group name that is not registered in either IAM or system groups.
    def test_create_command_with_unregistered_groupname(self):
        response = self.client.post(
            reverse('api:events:command-list'), {
                'shell': 'system',
                'line': 'pwd',
                'username': self.username,
                'groupname': 'docker', # Group name not registered in IAM or system groups
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Test command creation with a group name registered only in IAM groups.
    def test_create_command_with_iam_groupname_only(self):
        group = Group.objects.create(
            name='docker',
            display_name=get_random_string(128),
        )
        response = self.client.post(
            reverse('api:events:command-list'), {
                'shell': 'system',
                'line': 'pwd',
                'username': self.username,
                'groupname': group.name,
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cmd = Command.objects.get(pk=response.data['id'])
        self.assertEqual(cmd.username, self.username)
        self.assertEqual(cmd.groupname, group.name)  # For non-system users, ensure groupname is 'alpacon'.

    # Test command creation with a group name registered only in system groups.
    def test_create_command_with_system_groupname_only(self):
        SystemGroup.objects.create(server=self.server, gid=2010, groupname='docker')
        response = self.client.post(
            reverse('api:events:command-list'), {
                'shell': 'system',
                'line': 'pwd',
                'username': self.username,
                'groupname': 'docker',
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cmd = Command.objects.get(pk=response.data['id'])
        self.assertEqual(cmd.username, self.username)
        self.assertEqual(cmd.groupname, 'docker')

class CommandPermissionTestCase(APITestCase):
    def setUp(self):
        self.password = get_random_string(16)
        self.user = User.objects.create_user(
            username='user',
            password=self.password,
        )
        self.owner = User.objects.create_user(
            username='owner',
            password=self.password,
        )
        self.staff = User.objects.create_user(
            username='staff',
            password=self.password,
            is_staff=True,
        )
        self.group_member = User.objects.create_user(
            username='group-member',
            password=self.password,
        )
        self.group = Group.objects.create(
            name=get_random_username(),
            display_name=get_random_string(128),
        )
        self.group.membership_set.create(user=self.owner, role='owner')
        self.group.membership_set.create(user=self.staff, role='manager')
        self.group.membership_set.create(user=self.group_member, role='member')

        self.server = Server.objects.create(name='testing', owner=self.owner, commissioned=True)
        self.server.osversion_set.create(
            name='ubuntu',
            version='22.04',
            platform='debian',
            platform_like='debian',
        )
        self.server.groups.add(self.group)
        self.server.sessions.create(
            remote_ip='127.0.0.1',
            channel_id='fake_channel1'
        )

        # Generally, system users and groups on this server are synchronized with alpacon.
        SystemUser.objects.create(server=self.server, uid=2010, gid=2000, username='root')


    # Allow access to other accounts, like 'root', for users with staff level or higher.
    # Test command creation with 'root' by staff user(+group manager)
    def test_create_command_with_root_by_staff(self):
        self.client.login(username='staff', password=self.password)
        response = self.client.post(
            reverse('api:events:command-list'), {
                'shell': 'system',
                'line': 'pwd',
                'username': 'root',
                'groupname': self.group.name,
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # Group managers, owners, and server owners are permitted access to 'root' or other accounts.
    # Test command creation with 'root' by group owner
    def test_create_command_with_root_by_group_owner(self):
        self.client.login(username='owner', password=self.password)
        response = self.client.post(
            reverse('api:events:command-list'), {
                'shell': 'system',
                'line': 'pwd',
                'username': 'root',
                'groupname': self.group.name,
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # Users below staff level and group members cannot execute commands as other accounts.
    # Test command creation with 'root' by group member
    def test_create_command_with_root_by_group_member(self):
        self.client.login(username='group-member', password=self.password)
        response = self.client.post(
            reverse('api:events:command-list'), {
                'shell': 'system',
                'line': 'pwd',
                'username': 'root',
                'groupname': self.group.name,
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # General users not in any group cannot execute commands as other accounts or themselves.
    # Test command creation with 'root' by user (general)
    def test_create_command_with_root_by_user(self):
        self.client.login(username='user', password=self.password)
        response = self.client.post(
            reverse('api:events:command-list'), {
                'shell': 'system',
                'line': 'pwd',
                'username': 'root',
                'groupname': 'alpacon', # default group name
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Prevents execution of commands with usernames or groupnames not registered in IAM or Proc, even for users with staff-level permissions or higher.
    def test_command_creation_with_unregistered_user_group(self):
        self.client.login(username='staff', password=self.password)
        response = self.client.post(
            reverse('api:events:command-list'), {
                'shell': 'system',
                'line': 'pwd',
                'username': 'unregistered',  # Use 'unregistered' to indicate absence in IAM/Proc
                'groupname': 'unregistered',  # Use 'unregistered' to indicate absence in IAM/Proc
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
