from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from servers.models import Server, Note
from iam.models import Group
from iam.test_user import get_random_username


User = get_user_model()


class NoteModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.server = Server.objects.create(name='testing', owner=self.user)
        self.content = get_random_string(512)

    def test_create(self):
        obj = Note.objects.create(
            server=self.server,
            author=self.user,
            content=self.content,
        )
        self.assertEquals(obj.server.pk, self.server.pk)
        self.assertEquals(obj.author.pk, self.user.pk)
        self.assertEquals(obj.content, self.content)


class NodeAPIViewTestCase(APITestCase):
    def setUp(self):
        self.username = get_random_username()
        self.password = get_random_string(16)
        self.content = get_random_string(512)
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
        )
        self.group = Group.objects.create(
            name=get_random_string(128),
            display_name=get_random_string(128)
        )
        self.group.membership_set.create(user=self.user, role='owner')
        self.server = Server.objects.create(name='testing', owner=self.user)
        self.server.groups.add(self.group)
        self.client.login(username=self.username, password=self.password)

    def test_create_content_only(self):
        response = self.client.post(
            reverse('api:servers:note-list'), {
                'server': self.server.pk,
                'content': self.content,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertEquals(response.data['content'], self.content)
        self.assertEquals(response.data['server'], self.server.pk)
        self.assertEquals(response.data['author'], self.user.pk)
        self.assertFalse(response.data['private'])
        self.assertFalse(response.data['pinned'])

    def test_create_full_attrs(self):
        response = self.client.post(
            reverse('api:servers:note-list'), {
                'server': self.server.pk,
                'content': self.content,
                'private': True,
                'pinned': True,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['private'])
        self.assertTrue(response.data['pinned'])

        obj = Note.objects.get(pk=response.data['id'])
        self.assertEquals(obj.content, self.content)

    def test_pin_note(self):
        response = self.client.post(
            reverse('api:servers:note-list'), {
                'server': self.server.pk,
                'content': self.content,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['pinned'])
        note_pk = response.data['id']
        self.assertFalse(Note.objects.get(pk=note_pk).pinned)

        response = self.client.patch(
            reverse('api:servers:note-detail', kwargs={'pk': note_pk}), {
                'pinned': True,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['pinned'])
        self.assertTrue(Note.objects.get(pk=note_pk).pinned)

        response = self.client.patch(
            reverse('api:servers:note-detail', kwargs={'pk': note_pk}), {
                'pinned': False,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['pinned'])
        self.assertFalse(Note.objects.get(pk=note_pk).pinned)

    def test_pin_overflow(self):
        response = self.client.post(
            reverse('api:servers:note-list'), {
                'server': self.server.pk,
                'content': get_random_string(512),
                'pinned': True,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('api:servers:note-list'), {
                'server': self.server.pk,
                'content': get_random_string(512),
                'pinned': True,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('api:servers:note-list'), {
                'server': self.server.pk,
                'content': get_random_string(512),
                'pinned': True,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

        # create should fail: pinned notes can be 3 at max per server
        response = self.client.post(
            reverse('api:servers:note-list'), {
                'server': self.server.pk,
                'content': get_random_string(512),
                'pinned': True,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

        # create should succeed, but update `pinned` will fail
        response = self.client.post(
            reverse('api:servers:note-list'), {
                'server': self.server.pk,
                'content': get_random_string(512),
            }
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        response = self.client.patch(
            reverse('api:servers:note-detail', kwargs={'pk': response.data['id']}), {
                'pinned': True,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

        # it should be still okay to add pinned notes to another server
        self.server2 = Server.objects.create(name='testing2', owner=self.user)
        response = self.client.post(
            reverse('api:servers:note-list'), {
                'server': self.server2.pk,
                'content': get_random_string(512),
                'pinned': True,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_delete_note(self):
        response = self.client.post(
            reverse('api:servers:note-list'), {
                'server': self.server.pk,
                'content': self.content,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        note_pk = response.data['id']

        response = self.client.delete(
            reverse('api:servers:note-detail', kwargs={'pk': note_pk})
        )
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_on_owned_server(self):
        server2 = Server.objects.create(name='testing2', owner=self.user)
        response = self.client.post(
            reverse('api:servers:note-list'), {
                'server': server2.pk,
                'content': get_random_string(512),
            }
        )
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_create_on_server_with_no_perm(self):
        user2 = User.objects.create_user(
            username=get_random_username(),
            password=get_random_string(32)
        )
        server2 = Server.objects.create(name='testing2', owner=user2)
        response = self.client.post(
            reverse('api:servers:note-list'), {
                'server': server2.pk,
                'content': get_random_string(512),
            }
        )
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
