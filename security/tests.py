from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from rest_framework import status

from rest_framework.test import APITestCase

from api.apitoken.models import APIToken
from security.models import CommandACL
from servers.models import Server

User = get_user_model()


class CommandACLTestCase(APITestCase):

    def setUp(self):
        self.password = get_random_string(16)
        self.user = User.objects.create_user(
            username='user',
            password=self.password,
        )
        self.user2 = User.objects.create_user(
            username='user2',
            password=self.password,
        )
        self.key = get_random_string(64)
        self.token = APIToken.objects.create(user=self.user, key=self.key)
        self.token2 = APIToken.objects.create(user=self.user2)

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

        self.client.login(username=self.user.username, password=self.password)

    def test_create(self):
        response = self.client.post(
            reverse('api:security:commandacl-list'), {
                'token': self.token.pk,
                'command': 'docker compose up -d'
            }
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_put(self):
        response = self.client.post(
            reverse('api:security:commandacl-list'), {
                'token': self.token.pk,
                'command': 'docker compose up -d'
            }
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        command_acl_id = response.data['id']

        response = self.client.put(reverse('api:security:commandacl-detail', args=(command_acl_id,)), {
            'token': self.token.pk,
            'command': 'docker *'
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse('api:security:commandacl-detail', args=(command_acl_id,)))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data['command'], 'docker *')

    # Attempt to create with token of another user
    def test_create_with_another_user_token(self):
        self.client.logout()
        self.client.login(username='user2', password=self.password)
        response = self.client.post(
            reverse('api:security:commandacl-list'), {
                'token': self.token.pk,
                'command': 'docker compose up -d'
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Verify visibility of other user's command_acl
    def test_visibility_of_other_user_command_acl(self):
        response = self.client.post(
            reverse('api:security:commandacl-list'), {
                'token': self.token.pk,
                'command': 'docker compose up -d'
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CommandACL.objects.count(), 1)

        self.client.logout()
        self.client.login(username='user2', password=self.password)
        response = self.client.get(
            reverse('api:security:commandacl-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Other user's command_acl is not visible
        self.assertEqual(CommandACL.objects.count(), 1)

    # Attempt to create command_acl with a disabled token
    def test_create_with_disabled_token(self):
        token = APIToken.objects.create(user=self.user, name='api-token-2', enabled=False)
        response = self.client.post(
            reverse('api:security:commandacl-list'), {
                'token': token.pk,
                'command': 'docker compose up -d'
            }
        )
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_duplicate_command(self):
        response = self.client.post(
            reverse('api:security:commandacl-list'), {
                'token': self.token.pk,
                'command': 'docker compose up -d'
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Cannot create a second Command ACL with the same token and command
        response = self.client.post(
            reverse('api:security:commandacl-list'), {
                'token': self.token.pk,
                'command': 'docker compose up -d'
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_with_duplicate_command(self):
        response = self.client.post(
            reverse('api:security:commandacl-list'), {
                'token': self.token.pk,
                'command': 'docker compose up -d'
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('api:security:commandacl-list'), {
                'token': self.token.pk,
                'command': 'docker ps'
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        command_acl_id = response.data['id']

        # Updating an existing Command ACL to a duplicate command results in an error
        response = self.client.put(reverse('api:security:commandacl-detail', args=(command_acl_id,)), {
            'token': self.token.pk,
            'command': 'docker compose up -d'
        })
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_delete(self):
        response = self.client.post(
            reverse('api:security:commandacl-list'), {
                'token': self.token.pk,
                'command': '*'
            }
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        command_id = response.data['id']

        response = self.client.delete(reverse('api:security:commandacl-detail', args=(command_id,)))
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(reverse('api:security:commandacl-detail', args=(command_id,)))
        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)


class CommandACLAuthTestCase(APITestCase):

    def setUp(self):
        self.password = get_random_string(16)
        self.user = User.objects.create_user(
            username='user',
            password=self.password,
        )
        self.user2 = User.objects.create_user(
            username='user2',
            password=self.password,
        )
        self.key = get_random_string(64)
        self.token = APIToken.objects.create(user=self.user, key=self.key)
        self.token2 = APIToken.objects.create(user=self.user2)

        # try using API token
        self.client.credentials(
            HTTP_AUTHORIZATION='token="%s"' % self.key
        )

    def test_list_with_api_access(self):
        response = self.client.get(
            reverse('api:security:commandacl-list'))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_with_api_access(self):
        response = self.client.post(
            reverse('api:security:commandacl-list'), {
                'token': self.token.pk,
                'command': 'docker compose up -d'
            }
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)


class CommandExecutionTestCase(APITestCase):

    def setUp(self):
        self.password = get_random_string(16)
        self.user = User.objects.create_user(
            username='user',
            password=self.password,
        )
        self.key = get_random_string(64)
        self.token = APIToken.objects.create(user=self.user, key=self.key)

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

        # try using API token
        self.client.credentials(
            HTTP_AUTHORIZATION='token="%s"' % self.key
        )

        CommandACL.objects.create(token=self.token, command='cd *')
        CommandACL.objects.create(token=self.token, command='docker compose -f * up -d')
        CommandACL.objects.create(token=self.token, command='ls *')
        CommandACL.objects.create(token=self.token, command='git clone *')
        CommandACL.objects.create(token=self.token, command='rm -rf /allowed/*')

    def test_allowed_commands(self):
        commands = [
            'cd /home/user/',
            'cd ../etc/',
            'docker compose -f /home/docker-compose.yml up -d',
            'ls /var/log/',
            'git clone https://example.com/repo.git',
            'rm -rf /allowed/specific_file',
        ]
        for command in commands:
            with self.subTest(command=command):
                response = self.client.post(
                    reverse('api:events:command-list'), {
                        'shell': 'system',
                        'line': command,
                        'username': self.user.username,
                        'server': self.server.pk,
                    }
                )
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_disallowed_commands(self):
        commands = [
            'docker compose -f /home/docker-compose.yml down',
            'docker ps',
            'rm -rf /not/allowed/',
            'git push origin master',
            'systemctl restart nginx',
            'pwd',
        ]
        for command in commands:
            with self.subTest(command=command):
                response = self.client.post(
                    reverse('api:events:command-list'), {
                        'shell': 'system',
                        'line': command,
                        'username': self.user.username,
                        'server': self.server.pk,
                    }
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
