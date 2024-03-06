from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from rest_framework.test import APITestCase
from rest_framework import status


User = get_user_model()


class LoginTestCase(APITestCase):
    def setUp(self):
        self.username = get_random_string(16)
        self.password = get_random_string(16)
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
        )

    def login(self):
        response = self.client.post(
            reverse('api:auth:login'), {
                'username': self.username,
                'password': self.password,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertTrue('token' in response.data)
        self.token = response.data['token']
        self.client.credentials(
            HTTP_AUTHORIZATION='token="%s"' % self.token
        )

    def test_login(self):
        self.login()
        response = self.client.get(reverse('api:auth:is-authenticated'))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['authenticated'])

    def test_unauthorized(self):
        response = self.client.get(reverse('api:auth:is-authenticated'))
        self.assertEquals(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['authenticated'])

    def test_already_logged_in(self):
        self.login()
        response = self.client.post(
            reverse('api:auth:login'), {
                'username': self.username,
                'password': self.password,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data['code'], 'already-logged-in')

    def test_logout(self):
        self.login()
        response = self.client.post(reverse('api:auth:logout'))
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse('api:auth:is-authenticated'))
        self.assertEquals(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['authenticated'])

    def test_fake_logout(self):
        response = self.client.get(reverse('api:auth:is-authenticated'))
        self.assertEquals(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['authenticated'])

        response = self.client.post(reverse('api:auth:logout'))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)


class PasswordChangeTestCase(APITestCase):
    def setUp(self):
        self.username = get_random_string(16)
        self.password = get_random_string(16)
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
        )
        self.client.login(username=self.username, password=self.password)

    def test_change_password(self):
        new_password = get_random_string(16)
        response = self.client.post(reverse('api:auth:change-password'), {
            'password': self.password,
            'new_password': new_password,
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        
        # current session should be alive.
        response = self.client.get(reverse('api:auth:is-authenticated'))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['authenticated'])

        # test new password
        self.client.logout()
        self.assertFalse(self.client.login(username=self.username, password=self.password))
        self.assertTrue(self.client.login(username=self.username, password=new_password))

    def test_wrong_password(self):
        new_password = get_random_string(16)
        response = self.client.post(reverse('api:auth:change-password'), {
            'password': get_random_string(16),
            'new_password': new_password,
        })
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_password(self):
        new_password = get_random_string(16)
        response = self.client.post(reverse('api:auth:change-password'), {
            'new_password': new_password,
        })
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_easy_password(self):
        response = self.client.post(reverse('api:auth:change-password'), {
            'password': self.password,
            'new_password': '1234567890',
        })
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
