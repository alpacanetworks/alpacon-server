from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework.test import APITestCase
from rest_framework import status

from proc.models import SystemUser
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
            is_staff=True,
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
        self.server.sessions.create(
            remote_ip='127.0.0.1',
            channel_id='fake_channel1'
        )
        self.server.groups.add(self.group)

        # Generally, system users and groups on this server are synchronized with alpacon.
        SystemUser.objects.create(server=self.server, uid=2010, gid=2000, username=self.username, iam_user=self.user)


class UploadedFileUserAPIViewTestCase(FileTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username=self.username, password=self.password)

    # User's file upload request to Alpacon Server
    def test_upload_request(self):
        content = SimpleUploadedFile('test.txt', b'alpacon-test', content_type='text/plain')

        response = self.client.post(
            reverse('api:websh:uploadedfile-list'), {
                'server': self.server.pk,
                'content': content,
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

class FilePermissionTestCase(APITestCase):
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
        self.server.groups.add(self.group)
        self.path = "/user/younghwan/alpaca/test.txt"

        # Generally, system users and groups on this server are synchronized with alpacon.
        SystemUser.objects.create(server=self.server, uid=2010, gid=2000, username=self.owner.username, iam_user=self.owner)
        SystemUser.objects.create(server=self.server, uid=2011, gid=2000, username=self.user.username, iam_user=self.user)
        SystemUser.objects.create(server=self.server, uid=2012, gid=2000, username=self.staff.username, iam_user=self.staff)
        SystemUser.objects.create(server=self.server, uid=2013, gid=2000, username=self.superuser.username, iam_user=self.superuser)
        SystemUser.objects.create(server=self.server, uid=2014, gid=2000, username=self.group_member.username, iam_user=self.group_member)
        SystemUser.objects.create(server=self.server, uid=2015, gid=2000, username=self.group_manager.username, iam_user=self.group_manager)
        SystemUser.objects.create(server=self.server, uid=2016, gid=2000, username=self.group_owner.username, iam_user=self.group_owner)


    def test_upload_request_owner(self):
        self.client.login(username='owner', password=self.password)
        content = SimpleUploadedFile('test.txt', b'alpacon-test', content_type='text/plain')

        response = self.client.post(
            reverse('api:websh:uploadedfile-list'), {
                'server': self.server.pk,
                'content': content
            }, format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # User's file upload request to Alpacon Server
    def test_upload_request_user(self):
        self.client.login(username='user', password=self.password)
        content = SimpleUploadedFile('test.txt', b'alpacon-test', content_type='text/plain')

        response = self.client.post(
            reverse('api:websh:uploadedfile-list'), {
                'server': self.server.pk,
                'content': content
            }, format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_request_staff(self):
        self.client.login(username='staff', password=self.password)
        content = SimpleUploadedFile('test.txt', b'alpacon-test', content_type='text/plain')

        response = self.client.post(
            reverse('api:websh:uploadedfile-list'), {
                'server': self.server.pk,
                'content': content
            }, format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_upload_request_superuser(self):
        self.client.login(username='superuser', password=self.password)
        content = SimpleUploadedFile('test.txt', b'alpacon-test', content_type='text/plain')

        response = self.client.post(
            reverse('api:websh:uploadedfile-list'), {
                'server': self.server.pk,
                'content': content
            }, format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_upload_request_group_member(self):
        self.client.login(username='group-member', password=self.password)
        content = SimpleUploadedFile('test.txt', b'alpacon-test', content_type='text/plain')

        response = self.client.post(
            reverse('api:websh:uploadedfile-list'), {
                'server': self.server.pk,
                'content': content
            }, format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_upload_request_group_manager(self):
        self.client.login(username='group-manager', password=self.password)
        content = SimpleUploadedFile('test.txt', b'alpacon-test', content_type='text/plain')

        response = self.client.post(
            reverse('api:websh:uploadedfile-list'), {
                'server': self.server.pk,
                'content': content
            }, format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_upload_request_group_owner(self):
        self.client.login(username='group-owner', password=self.password)
        content = SimpleUploadedFile('test.txt', b'alpacon-test', content_type='text/plain')

        response = self.client.post(
            reverse('api:websh:uploadedfile-list'), {
                'server': self.server.pk,
                'content': content
            }, format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_download_request_owner(self):
        self.client.login(username='owner', password=self.password)
        response = self.client.post(
            reverse('api:websh:downloadedfile-list'), {
                'path': self.path,
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_download_request_user(self):
        self.client.login(username='user', password=self.password)
        response = self.client.post(
            reverse('api:websh:downloadedfile-list'), {
                'path': self.path,
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_download_request_staff(self):
        self.client.login(username='staff', password=self.password)
        response = self.client.post(
            reverse('api:websh:downloadedfile-list'), {
                'path': self.path,
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_download_request_superuser(self):
        self.client.login(username='superuser', password=self.password)
        response = self.client.post(
            reverse('api:websh:downloadedfile-list'), {
                'path': self.path,
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_download_request_group_member(self):
        self.client.login(username='group-member', password=self.password)
        response = self.client.post(
            reverse('api:websh:downloadedfile-list'), {
                'path': self.path,
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_download_request_group_manager(self):
        self.client.login(username='group-manager', password=self.password)
        response = self.client.post(
            reverse('api:websh:downloadedfile-list'), {
                'path': self.path,
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_download_request_group_owner(self):
        self.client.login(username='group-owner', password=self.password)
        response = self.client.post(
            reverse('api:websh:downloadedfile-list'), {
                'path': self.path,
                'server': self.server.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # Blocks download/upload requests using usernames or groupnames not registered in IAM or Proc, even for users with staff-level permissions or higher.
    def test_download_request_with_unregistered_user_group(self):
        self.client.login(username='superuser', password=self.password)
        response = self.client.post(
            reverse('api:websh:downloadedfile-list'), {
                'path': self.path,
                'server': self.server.pk,
                'username': 'unregistered',  # Use 'unregistered' to indicate absence in IAM/Proc
                'groupname': 'unregistered',  # Use 'unregistered' to indicate absence in IAM/Proc
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_request_with_unregistered_user_group(self):
        self.client.login(username='superuser', password=self.password)
        content = SimpleUploadedFile('test.txt', b'alpacon-test', content_type='text/plain')

        response = self.client.post(
            reverse('api:websh:uploadedfile-list'), {
                'server': self.server.pk,
                'username': 'unregistered',  # Use 'unregistered' to indicate absence in IAM/Proc
                'groupname': 'unregistered',  # Use 'unregistered' to indicate absence in IAM/Proc
                'content': content,
            }, format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Staff-level or higher cannot use other IAM accounts, only system user accounts allowed
    def test_staff_download_as_other(self):
        self.client.login(username='staff', password=self.password)
        response = self.client.post(
            reverse('api:websh:downloadedfile-list'), {
                'path': self.path,
                'server': self.server.pk,
                'username': 'superuser',  # Use other accounts
                'groupname': 'alpacon',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Below-staff cannot download/upload for others.
    def test_nonstaff_download_as_other_denied(self):
        self.client.login(username='user', password=self.password)
        response = self.client.post(
            reverse('api:websh:downloadedfile-list'), {
                'path': self.path,
                'server': self.server.pk,
                'username': 'superuser',  # Use other accounts
                'groupname': 'alpacon',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)