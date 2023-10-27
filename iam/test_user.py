from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from rest_framework.test import APITestCase
from rest_framework import status


User = get_user_model()


def get_random_username():
    return 'a' + get_random_string(16, 'abcdefghijklmnopqrstuvwxyz0123456789-_')


class UserTestMixin:
    def create_user_and_login(self, **kwargs):
        self.password = get_random_string(32)
        self.user = User.objects.create_user(
            username=get_random_username(),
            password=self.password,
            **kwargs
        )
        self.client.login(username=self.user.username, password=self.password)

    def create_user_via_api(self, **kwargs):
        username = get_random_username()
        return self.client.post(reverse('api:iam:user-list'), {
            'username': username,
            'password': get_random_string(32),
            'first_name': get_random_string(8),
            'last_name': get_random_string(8),
            'email': username + '@alpacon.io',
            **kwargs
        })


class SelfUserTestCase(UserTestMixin, APITestCase):
    def setUp(self):
        self.create_user_and_login()

    def test_get_user(self):
        response = self.client.get(reverse('api:iam:user-detail', args=('-',)))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data['id'], str(self.user.id))
        self.assertEquals(response.data['username'], self.user.username)

        response = self.client.get(reverse('api:iam:user-detail', args=(self.user.id,)))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data['id'], str(self.user.id))

    def test_change_password(self):
        """
        Password will remain the same without an error.
        """
        new_password = get_random_string(32)
        response = self.client.patch(
            reverse('api:iam:user-detail', args=('-',)), {
                'password': new_password,
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('password', response.data)
        self.client.logout()
        self.assertFalse(self.client.login(
            username=self.user.username,
            password=new_password,
        ))

    def test_change_username(self):
        """
        Username will remain the same without an error.
        """
        new_username = get_random_username()
        response = self.client.patch(
            reverse('api:iam:user-detail', args=('-',)), {
                'username': new_username,
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response = self.client.get(
            reverse('api:iam:user-detail', args=('-',))
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data['username'], self.user.username)

    def test_change_information(self):
        response = self.client.patch(
            reverse('api:iam:user-detail', args=('-',)), {
                'first_name': 'First',
                'last_name': 'Last',
                'email': 'alice@bob.com',
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_delete_user(self):
        """
        Test deleting user accounts. After deletion, subsequent requests
        from the deleted user should be denied with 403 Forbidden.
        """
        response = self.client.delete(
            reverse('api:iam:user-detail', args=('-',))
        )
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get(
            reverse('api:iam:user-detail', args=('-',))
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)


class UserTestCase(UserTestMixin, APITestCase):
    def setUp(self):
        self.create_user_and_login()

    def test_create_by_user(self):
        self.assertEquals(
            self.create_user_via_api().status_code,
            status.HTTP_403_FORBIDDEN
        )
        self.assertEquals(
            self.create_user_via_api(is_staff=True).status_code,
            status.HTTP_403_FORBIDDEN
        )
        self.assertEquals(
            self.create_user_via_api(is_staff=True, is_superuser=True).status_code,
            status.HTTP_403_FORBIDDEN
        )

    def test_update_by_user(self):
        user = User.objects.create_user(
            username=get_random_username(),
            password=get_random_string(32),
        )
        response = self.client.patch(
            reverse('api:iam:user-detail', args=(user.id,)), {
                'first_name': get_random_string(8),
                'last_name': get_random_string(8),
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_by_user(self):
        user = User.objects.create_user(
            username=get_random_username(),
            password=get_random_string(32),
        )
        response = self.client.delete(
            reverse('api:iam:user-detail', args=(user.id,))
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)


class StaffTestCase(UserTestMixin, APITestCase):
    def setUp(self):
        self.create_user_and_login(is_staff=True)

    def test_create_by_staff(self):
        self.assertEquals(
            self.create_user_via_api().status_code,
            status.HTTP_201_CREATED
        )
        self.assertEquals(
            self.create_user_via_api(is_staff=True).status_code,
            status.HTTP_403_FORBIDDEN
        )
        self.assertEquals(
            self.create_user_via_api(is_staff=True, is_superuser=True).status_code,
            status.HTTP_403_FORBIDDEN
        )

    def test_update_by_staff(self):
        user = User.objects.create_user(
            username=get_random_username(),
            password=get_random_string(32),
        )
        response = self.client.patch(
            reverse('api:iam:user-detail', args=(user.id,)), {
                'first_name': get_random_string(8),
                'last_name': get_random_string(8),
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_update_privilege_by_staff(self):
        user = User.objects.create_user(
            username=get_random_username(),
            password=get_random_string(32),
        )
        response = self.client.patch(
            reverse('api:iam:user-detail', args=(user.id,)), {
                'is_staff': True,
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.patch(
            reverse('api:iam:user-detail', args=(user.id,)), {
                'is_staff': True,
                'is_superuser': True,
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_change_password_by_staff(self):
        user = User.objects.create_user(
            username=get_random_username(),
            password=get_random_string(32),
        )
        new_password = get_random_string(32)
        response = self.client.patch(
            reverse('api:iam:user-detail', args=(user.id,)), {
                'password': new_password,
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('password', response.data)
        self.client.logout()
        self.assertTrue(self.client.login(
            username=user.username,
            password=new_password,
        ))

    def test_empty_password_by_staff(self):
        old_password = get_random_string(32)
        user = User.objects.create_user(
            username=get_random_username(),
            password=old_password,
        )
        response = self.client.patch(
            reverse('api:iam:user-detail', args=(user.id,)), {
                'first_name': 'First',
                'last_name': 'Last',
                'password': '',
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('password', response.data)
        self.client.logout()
        self.assertTrue(self.client.login(
            username=user.username,
            password=old_password,
        ))

    def test_delete_by_staff(self):
        user = User.objects.create_user(
            username=get_random_username(),
            password=get_random_string(32),
        )
        response = self.client.delete(
            reverse('api:iam:user-detail', args=(user.id,))
        )
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

        user = User.objects.create_user(
            username=get_random_username(),
            password=get_random_string(32),
            is_staff=True,
        )
        response = self.client.delete(
            reverse('api:iam:user-detail', args=(user.id,))
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.delete(
            reverse('api:iam:user-detail', args=('-',))
        )
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)


class SuperuserTestCase(UserTestMixin, APITestCase):
    def setUp(self):
        self.create_user_and_login(is_staff=True, is_superuser=True)

    def test_create_by_superuser(self):
        self.create_user_and_login(is_staff=True, is_superuser=True)
        self.assertEquals(
            self.create_user_via_api().status_code,
            status.HTTP_201_CREATED
        )
        self.assertEquals(
            self.create_user_via_api(is_staff=True).status_code,
            status.HTTP_201_CREATED
        )
        self.assertEquals(
            self.create_user_via_api(is_staff=True, is_superuser=True).status_code,
            status.HTTP_201_CREATED
        )

    def test_update_privilege_by_superuser(self):
        user = User.objects.create_user(
            username=get_random_username(),
            password=get_random_string(32),
        )
        response = self.client.patch(
            reverse('api:iam:user-detail', args=(user.id,)), {
                'is_staff': True,
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        response = self.client.patch(
            reverse('api:iam:user-detail', args=(user.id,)), {
                'is_staff': True,
                'is_superuser': True,
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_delete_by_superuser(self):
        user = User.objects.create_user(
            username=get_random_username(),
            password=get_random_string(32),
        )
        response = self.client.delete(
            reverse('api:iam:user-detail', args=(user.id,))
        )
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

        user = User.objects.create_user(
            username=get_random_username(),
            password=get_random_string(32),
            is_staff=True,
        )
        response = self.client.delete(
            reverse('api:iam:user-detail', args=(user.id,))
        )
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

        user = User.objects.create_user(
            username=get_random_username(),
            password=get_random_string(32),
            is_staff=True,
            is_superuser=True,
        )
        response = self.client.delete(
            reverse('api:iam:user-detail', args=(user.id,))
        )
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_degrade_last_superuser(self):
        response = self.client.patch(
            reverse('api:iam:user-detail', args=('-')), {
                'is_superuser': False,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_last_superuser(self):
        response = self.client.delete(
            reverse('api:iam:user-detail', args=('-'))
        )
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
