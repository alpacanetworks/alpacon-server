import uuid
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.core.exceptions import ObjectDoesNotExist

from rest_framework.test import APITestCase
from rest_framework import status

from api.apiclient.models import APIClient
from api.apiclient.tokens import JWTRefreshToken


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
        response = self.client.get(reverse('api:status'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='id="%s", key="%s"' % (self.client_id, self.client_key)
        )
        response = self.client.get(reverse('api:status'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_auth_without_quotes(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='id=%s, key=%s' % (self.client_id, self.client_key)
        )
        response = self.client.get(reverse('api:status'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_auth_no_space(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='id="%s",key="%s"' % (self.client_id, self.client_key)
        )
        response = self.client.get(reverse('api:status'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_auth_no_key_1(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='id="%s"' % (self.client_id)
        )
        response = self.client.get(reverse('api:status'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_no_key_2(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='id="%s", key=""' % (self.client_id)
        )
        response = self.client.get(reverse('api:status'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_no_id_1(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='key="%s"' % (self.client_key)
        )
        response = self.client.get(reverse('api:status'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_no_id_2(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='id="", key="%s"' % (self.client_key)
        )
        response = self.client.get(reverse('api:status'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_empty(self):
        self.client.credentials(HTTP_AUTHORIZATION='')
        response = self.client.get(reverse('api:status'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_malformed_1(self):
        self.client.credentials(HTTP_AUTHORIZATION='aaaaa')
        response = self.client.get(reverse('api:status'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_malformed_2(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='id="%s", key="%s"' % ('a'*128, 'b'*128)
        )
        response = self.client.get(reverse('api:status'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_malformed_3(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='id="%s", key="%s"' % ('a'*512, 'b'*512)
        )
        response = self.client.get(reverse('api:status'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_1(self):
        """
        APIClient should be denied on user login.
        """
        self.client.login(username=self.client_id, password=self.client_key)
        response = self.client.get(reverse('api:status'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_2(self):
        """
        APIClient should be denied on user login.
        """
        self.client.login(id=self.client_id, key=self.client_key)
        response = self.client.get(reverse('api:status'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class JWTLoginTestCase(APITestCase):
    """
    When logging in using ID and key, check the APIclient model and test whether the token is returned normally.
    """

    def setUp(self):
        self.client_id = uuid.uuid4()
        self.client_key = get_random_string(16)
    
        self.user = User.objects.create_user(username='testuser')
        self.api_client = APIClient.objects.create_api_client(
            owner=self.user,
            id=self.client_id,
            key=self.client_key,
        )
    
    def jwtlogin(self):
        response = self.client.post(
            reverse('api:apiclient:jwt:login'), {
                'id': self.client_id,
                'key': self.client_key,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertTrue('refresh' in response.data)
        self.assertTrue('access' in response.data)
        self.token = response.data['access']
        self.client.credentials(
            HTTP_AUTHORIZATION='Bearer %s' % self.token
        )

    def test_jwtlogin(self):
        self.jwtlogin()
        response = self.client.get(reverse('api:auth:is-authenticated'))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['authenticated'])

    def test_unauthorized(self):
        response = self.client.get(reverse('api:auth:is-authenticated'))
        self.assertEquals(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['authenticated'])
    
    def test_jwtlogin_no_id_key(self):
        response = self.client.post(
            reverse('api:apiclient:jwt:login'), { }
        )
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_jwtlogin_no_id(self):
        response = self.client.post(
            reverse('api:apiclient:jwt:login'), {
                'key': self.client_key,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_jwtlogin_no_key(self):
        response = self.client.post(
            reverse('api:apiclient:jwt:login'), {
                'id': self.client_id,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_jwtlogin_invalid_id_and_key(self):
        response = self.client.post(
            reverse('api:apiclient:jwt:login'), {
                'id': 'a'*128,
                'key': 'b'*128,
        }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class JWTRefreshTestCase(APITestCase):
    """
    When a refresh token is entered in the header, it verifies the refresh token and tests whether the new access token is returned normally.
    """

    def test_jwtrefresh(self):
        refresh = JWTRefreshToken()
        refresh["test_claim"] = "test_client_id"

        response = self.client.post(
            reverse('api:apiclient:jwt:refresh'), {
                "refresh": str(refresh)
            }
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertTrue('access' in response.data)
    
    def test_it_should_return_401_if_token_invalid(self):
        refresh = JWTRefreshToken()

        refresh.set_exp(lifetime=-timedelta(seconds=1))

        response = self.client.post(
            reverse('api:apiclient:jwt:refresh'), {
                "refresh": str(refresh)
            }
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "token_not_valid")


class JWTSessionTestCase(APITestCase):
    """
    When an expired access token is entered in the header, alpacon-server tests whether a 403 Forbidden error is generated.
    """

    def setUp(self):
        self.client_id = uuid.uuid4()
        self.client_key = get_random_string(16)
    
        self.user = User.objects.create_user(username='testuser')
        self.api_client = APIClient.objects.create_api_client(
            owner=self.user,
            id=self.client_id,
            key=self.client_key,
        )

    def test_session_connect(self):
        refresh = JWTRefreshToken.for_client(self.client_id)
        access = refresh.access_token
        self.client.credentials(
            HTTP_AUTHORIZATION='Bearer %s' % access
        )

        response = self.client.get(reverse('api:auth:is-authenticated'))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['authenticated'])

    def test_session_no_connect(self):
        refresh = JWTRefreshToken.for_client(self.client_id)
        access = refresh.access_token

        access.set_exp(lifetime=-timedelta(seconds=1))

        self.client.credentials(
            HTTP_AUTHORIZATION='Bearer %s' % access
        )

        response = self.client.get(reverse('api:auth:is-authenticated'))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)