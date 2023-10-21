from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework.test import APITestCase
from rest_framework import status

from servers.models import Server
from iam.models import Group
from iam.test_user import get_random_username
from websh.models import DownloadedFile, UploadedFile

User = get_user_model()


class FileTestCase(APITestCase):
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
        self.server = Server.objects.create(name='testing', owner=self.user)

        self.server.osversion_set.create(
            name='ubuntu',
            version='22.04',
            platform='debian',
            platform_like='debian',
        )

        self.server.groups.add(self.group)


class UploadedFileUserAPIViewTestCase(FileTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username=self.username, password=self.password)

    # User's file upload request to Alpacon Server
    def test_download_request(self):
        content = SimpleUploadedFile('test.txt', b'alpacon-test', content_type='text/plain')

        response = self.client.post(
            reverse('api:websh:uploadedfile-list'), {
                'server': self.server.pk,
                'content': content
            }, format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class UploadedFileServerAPIViewTestCase(FileTestCase):

    def setUp(self):
        super().setUp()
        self.server_key = self.server.make_random_key()
        self.server.set_key(self.server_key)
        self.server.save()

        self.client.credentials(
            HTTP_AUTHORIZATION='id="%s", key="%s"' % (self.server.id, self.server_key)
        )

        content = SimpleUploadedFile('test.txt', b'alpacon-test', content_type='text/plain')

        self.obj = UploadedFile.objects.create(
            server=self.server,
            user=self.user,
            path="/user/younghwan/alpaca/test.txt",
            content=content
        )

    # Alpamon's file download request to Alpacon Server
    def test_download_request(self):
        response = self.client.get(
            reverse('api:websh:uploadedfile-download', kwargs={'pk': self.obj.pk}),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DownloadedFileUserAPIViewTestCase(FileTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username=self.username, password=self.password)
        self.path = "/user/younghwan/alpaca/test.txt"

    # User's file download request to Alpacon Server
    def test_download_request(self):
        response = self.client.post(
            reverse('api:websh:downloadedfile-list'), {
                'path': self.path,
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class DownloadedFileServerAPIViewTestCase(FileTestCase):
    def setUp(self):
        super().setUp()
        self.server_key = self.server.make_random_key()
        self.server.set_key(self.server_key)
        self.server.save()

        self.client.credentials(
            HTTP_AUTHORIZATION='id="%s", key="%s"' % (self.server.id, self.server_key)
        )

        self.obj = DownloadedFile.objects.create(
            server=self.server,
            user=self.user,
            path="/user/younghwan/alpaca/test.txt",
        )

    # Alpamon's upload request to Alpacon Server
    def test_upload_request(self):
        content = SimpleUploadedFile('test.txt', b'alpacon-test', content_type='text/plain')

        response = self.client.post(
            reverse('api:websh:downloadedfile-upload', kwargs={'pk': self.obj.pk}),
            data={'content': content}, format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)