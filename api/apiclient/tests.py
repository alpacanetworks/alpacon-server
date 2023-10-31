from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from rest_framework.test import APITestCase
from rest_framework import status

from api.apiclient.models import APIClient


User = get_user_model()


class APIClientModelTestCase(TestCase):
    """
    Test APIClient model and its member functions work properly.
    """
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')

    def test_make_random_key(self):
        """
        Test `make_random_key` results are as expected.
        """
        key = APIClient.make_random_key()
        self.assertEqual(len(key), 32)
        key = APIClient.make_random_key(length=64)
        self.assertEqual(len(key), 64)
        key = APIClient.make_random_key(length=16, allowed_chars='a')
        self.assertEqual(key, 'a'*16)

    def test_client_check_key(self):
        """
        Test `check_key` properly authenticates clients' id and key.
        """
        client1 = APIClient(owner=self.user)
        client2 = APIClient(owner=self.user)
        self.id1 = client1.id
        self.id2 = client2.id

        self.key1 = client1.make_random_key()
        client1.set_key(self.key1)
        client1.save()
        self.key2 = client2.make_random_key()
        client2.set_key(self.key2)
        client2.save()

        client1 = APIClient.objects.get(id=self.id1)
        client2 = APIClient.objects.get(id=self.id2)

        self.assertTrue(client1.check_key(self.key1))
        self.assertTrue(client2.check_key(self.key2))
        self.assertFalse(client1.check_key(self.key2))
        self.assertFalse(client2.check_key(self.key1))
        self.assertFalse(client1.check_key(None))
        self.assertFalse(client1.check_key(''))

    def test_unset_key(self):
        """
        APIClient with unset keys should not pass `check_key`.
        """
        client = APIClient.objects.create(owner=self.user)

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

    def test_unusable_key(self):
        """
        APIClient with unusable keys should have `has_usable_key` false.
        """
        client = APIClient.objects.create(owner=self.user)
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
        (client, key) = APIClient.objects.create_api_client(self.user)
        self.assertTrue(client.check_key(key))
        self.assertFalse(client.check_key(None))
        self.assertFalse(client.check_key(''))

    def test_get_valid_client(self):
        """
        `get_valid_client` should return correct client object
        """
        (client, key) = APIClient.objects.create_api_client(self.user)
        obj = APIClient.objects.get_valid_client(id=client.id, key=key)
        self.assertEqual(client.id, obj.id)

    def test_disabled_client(self):
        (client, key) = APIClient.objects.create_api_client(self.user, enabled=False)
        with self.assertRaises(ObjectDoesNotExist):
            APIClient.objects.get_valid_client(id=client.id, key=key)

    def test_invalid_client_key(self):
        (client, key) = APIClient.objects.create_api_client(self.user, enabled=False)
        with self.assertRaises(ObjectDoesNotExist):
            APIClient.objects.get_valid_client(id=client.id, key=key[:-1])

    def test_empty_client_key(self):
        (client, key) = APIClient.objects.create_api_client(self.user, enabled=False)
        with self.assertRaises(ObjectDoesNotExist):
            APIClient.objects.get_valid_client(id=client.id, key='')

    def test_null_client_key(self):
        (client, key) = APIClient.objects.create_api_client(self.user, enabled=False)
        with self.assertRaises(ObjectDoesNotExist):
            APIClient.objects.get_valid_client(id=client.id, key=None)


class APIClientAuthTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        (client, self.client_key) = APIClient.objects.create_api_client(self.user)
        self.client_id = str(client.id)

    def test_no_auth(self):
        response = self.client.get(reverse('api:index'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='id="%s", key="%s"' % (self.client_id, self.client_key)
        )
        response = self.client.get(reverse('api:index'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_auth_without_quotes(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='id=%s, key=%s' % (self.client_id, self.client_key)
        )
        response = self.client.get(reverse('api:index'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_auth_no_space(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='id="%s",key="%s"' % (self.client_id, self.client_key)
        )
        response = self.client.get(reverse('api:index'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_auth_no_key_1(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='id="%s"' % (self.client_id)
        )
        response = self.client.get(reverse('api:index'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_no_key_2(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='id="%s", key=""' % (self.client_id)
        )
        response = self.client.get(reverse('api:index'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_no_id_1(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='key="%s"' % (self.client_key)
        )
        response = self.client.get(reverse('api:index'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_no_id_2(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='id="", key="%s"' % (self.client_key)
        )
        response = self.client.get(reverse('api:index'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_empty(self):
        self.client.credentials(HTTP_AUTHORIZATION='')
        response = self.client.get(reverse('api:index'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_malformed_1(self):
        self.client.credentials(HTTP_AUTHORIZATION='aaaaa')
        response = self.client.get(reverse('api:index'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_malformed_2(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='id="%s", key="%s"' % ('a'*128, 'b'*128)
        )
        response = self.client.get(reverse('api:index'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_malformed_3(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='id="%s", key="%s"' % ('a'*512, 'b'*512)
        )
        response = self.client.get(reverse('api:index'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_1(self):
        """
        APIClient should be denied on user login.
        """
        self.client.login(username=self.client_id, password=self.client_key)
        response = self.client.get(reverse('api:index'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_2(self):
        """
        APIClient should be denied on user login.
        """
        self.client.login(id=self.client_id, key=self.client_key)
        response = self.client.get(reverse('api:index'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
