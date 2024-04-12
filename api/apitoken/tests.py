from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from rest_framework.test import APITestCase
from rest_framework import status

from api.apitoken.models import APIToken


User = get_user_model()


class APITokenModelTestCase(TestCase):
    """
    Test APIToken model and its member functions work properly.
    """

    def setUp(self):
        self.user = User.objects.create_user(username='api-token-user-1')

    def test_create_api_token(self):
        token = APIToken.objects.create(user=self.user)
        self.assertIsNotNone(token.key)
        self.assertIsNone(token.expires_at)
        APIToken.objects.get_valid_user(token.key)

    def test_user_match(self):
        token = APIToken.objects.create(user=self.user)
        (user, token_) = APIToken.objects.get_valid_user(token.key)
        self.assertEquals(user.pk, self.user.pk)
        self.assertEqual(token.pk, token_.pk)

    def test_create_api_token_manual(self):
        token = APIToken.objects.create(user=self.user, key='abcd1234')
        self.assertEquals(token.key, 'abcd1234')
        APIToken.objects.get_valid_user('abcd1234')

    def test_disabled_api_token(self):
        token = APIToken.objects.create(user=self.user, enabled=False)
        with self.assertRaises(ObjectDoesNotExist):
            APIToken.objects.get_valid_user(token.key)

    def test_wrong_api_token(self):
        APIToken.objects.create(user=self.user, enabled=False)
        with self.assertRaises(ObjectDoesNotExist):
            APIToken.objects.get_valid_user('abcd1234')

    def test_empty_api_token(self):
        APIToken.objects.create(user=self.user, enabled=False)
        with self.assertRaises(ObjectDoesNotExist):
            APIToken.objects.get_valid_user('')

    def test_null_api_token(self):
        APIToken.objects.create(user=self.user, enabled=False)
        with self.assertRaises(ObjectDoesNotExist):
            APIToken.objects.get_valid_user(None)

    def test_api_token_with_expires_at(self):
        token = APIToken.objects.create(
            user=self.user,
            expires_at=timezone.now()+timedelta(weeks=1),
        )
        self.assertIsNotNone(token.key)
        self.assertIsNotNone(token.expires_at)
        APIToken.objects.get_valid_user(token.key)

    def test_expired_api_token(self):
        token = APIToken.objects.create(
            user=self.user,
            expires_at=timezone.now()-timedelta(weeks=1),
        )
        with self.assertRaises(ObjectDoesNotExist):
            APIToken.objects.get_valid_user(token.key)

    def test_delete_expired_tokens(self):
        APIToken.objects.create(
            user=self.user,
            expires_at=timezone.now()-timedelta(weeks=1),
        )
        self.assertEquals(APIToken.objects.delete_expired_tokens()[0], 1)


class APITokenAuthTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='api-token-user-2')
        self.token = APIToken.objects.create(user=self.user).key

    def test_no_auth(self):
        response = self.client.get(reverse('api:status'))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='token="%s"' % self.token
        )
        response = self.client.get(reverse('api:status'))
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_api_auth_without_quotes(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='token=%s' % self.token
        )
        response = self.client.get(reverse('api:status'))
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_api_auth_invalid_token_1(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='token="%s"' % self.token[:-1]
        )
        response = self.client.get(reverse('api:status'))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_invalid_token_2(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='token="%s"' % (self.token+'x')
        )
        response = self.client.get(reverse('api:status'))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_empty_token(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='token=""'
        )
        response = self.client.get(reverse('api:status'))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_empty(self):
        self.client.credentials(HTTP_AUTHORIZATION='')
        response = self.client.get(reverse('api:status'))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_malformed_1(self):
        self.client.credentials(HTTP_AUTHORIZATION='aaaaa')
        response = self.client.get(reverse('api:status'))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_malformed_2(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='token="%s"' % 'a'*128
        )
        response = self.client.get(reverse('api:status'))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_auth_malformed_3(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='token="%s"' % 'a'*1024
        )
        response = self.client.get(reverse('api:status'))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_1(self):
        """
        APIToken should be denied on user login.
        """
        self.client.login(username=self.user.username, password=self.token)
        response = self.client.get(reverse('api:status'))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_2(self):
        """
        APIToken should be denied on user login.
        """
        self.client.login(id=self.user.id, key=self.token)
        response = self.client.get(reverse('api:status'))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)


class APITokenViewSetTestCase(APITestCase):
    def setUp(self):
        self.password = 'abcd1234'
        self.user = User.objects.create_user(
            username='api-token-user-3',
            password=self.password,
        )
        self.client.login(username=self.user.username, password=self.password)

    def test_create(self):
        response = self.client.post(reverse('api:auth:apitoken:apitoken-list') ,{
            'name': 'api-token',
        })
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('id' in response.data)
        self.assertTrue('key' in response.data)
        self.assertTrue('enabled' in response.data)
        self.assertTrue(response.data['enabled'])
        self.assertTrue('expires_at' in response.data)
        self.assertIsNone(response.data['expires_at'])

    def test_create_with_duplicate_name(self):
        response = self.client.post(reverse('api:auth:apitoken:apitoken-list'), {
            'name' : 'api-token-1',
        })
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(reverse('api:auth:apitoken:apitoken-list'), {
            'name' : 'api-token-1',
        })
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_with_duplicate_name(self):
        response = self.client.post(reverse('api:auth:apitoken:apitoken-list'), {
            'name' : 'api-token-1',
        })
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(reverse('api:auth:apitoken:apitoken-list'), {
            'name' : 'api-token-2',
        })
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        token_id = response.data['id']

        response = self.client.put(reverse('api:auth:apitoken:apitoken-detail', args=(token_id,)), {
            'name' : 'api-token-1',
            'enabled': False,
        })
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_create_options(self):
        expiration = timezone.now()+timedelta(weeks=1)
        response = self.client.post(reverse('api:auth:apitoken:apitoken-list'), {
            'name': 'api-token',
            'expires_at': expiration,
            'enabled': False,
        })
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertEquals(parse_datetime(response.data['expires_at']), expiration)
        self.assertEquals(response.data['enabled'], False)

    def test_create_invalid_options(self):
        """
        Past time for `expires_at` is invalid.
        """
        response = self.client.post(reverse('api:auth:apitoken:apitoken-list'), {
            'expires_at': timezone.now()-timedelta(weeks=1)
        })
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_api_access(self):
        # create and obtain API token
        response = self.client.post(reverse('api:auth:apitoken:apitoken-list'), {
            'name' : 'api-token'
        })
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        token = response.data['key']

        # logout and verify
        self.client.logout()
        response = self.client.get(reverse('api:status'))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

        # try using API token
        self.client.credentials(
            HTTP_AUTHORIZATION='token="%s"' % token
        )
        response = self.client.get(reverse('api:status'))
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    # Deny API token creation via API token access
    def test_create_via_api_access(self):
        # create and obtain API token
        response = self.client.post(reverse('api:auth:apitoken:apitoken-list'), {
            'name' : 'api-token'
        })
        token = response.data['key']

        # logout and verify
        self.client.logout()

        # try using API token
        self.client.credentials(
            HTTP_AUTHORIZATION='token="%s"' % token
        )
        response = self.client.post(reverse('api:auth:apitoken:apitoken-list'))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list(self):
        response = self.client.post(reverse('api:auth:apitoken:apitoken-list'), {
            'name' : 'api-token'
        })
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(reverse('api:auth:apitoken:apitoken-list'))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data['count'], 1)
        self.assertEquals(len(response.data['results']), 1)

    def test_get(self):
        response = self.client.post(reverse('api:auth:apitoken:apitoken-list'), {
            'name' : 'api-token'
        })
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        token_id = response.data['id']

        response = self.client.get(reverse('api:auth:apitoken:apitoken-detail', args=(token_id,)))
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_put(self):
        response = self.client.post(reverse('api:auth:apitoken:apitoken-list'), {
            'name': 'api-token',
            'enabled': True,
            'expires_at': timezone.now()+timedelta(weeks=1),
        })
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        token_id = response.data['id']

        response = self.client.put(reverse('api:auth:apitoken:apitoken-detail', args=(token_id,)), {
            'name': 'api-token',
            'enabled': False,
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse('api:auth:apitoken:apitoken-detail', args=(token_id,)))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data['enabled'], False)
        self.assertIsNotNone(response.data['expires_at'])

    def test_patch(self):
        response = self.client.post(reverse('api:auth:apitoken:apitoken-list'), {
            'name': 'api-token',
            'enabled': True,
            'expires_at': timezone.now()+timedelta(weeks=1),
        })
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        token_id = response.data['id']

        response = self.client.patch(reverse('api:auth:apitoken:apitoken-detail', args=(token_id,)), {
            'name' : 'api-token',
            'enabled': False,
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse('api:auth:apitoken:apitoken-detail', args=(token_id,)))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data['enabled'], False)
        self.assertIsNotNone(response.data['expires_at'])

        response = self.client.patch(reverse('api:auth:apitoken:apitoken-detail', args=(token_id,)), {
            'name': 'api-token',
            'expires_at': None,
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse('api:auth:apitoken:apitoken-detail', args=(token_id,)))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data['enabled'], False)
        self.assertIsNone(response.data['expires_at'])

    def test_delete(self):
        response = self.client.post(reverse('api:auth:apitoken:apitoken-list'), {
            'name': 'api-token',
        })
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        token_id = response.data['id']

        response = self.client.delete(reverse('api:auth:apitoken:apitoken-detail', args=(token_id,)))
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get(reverse('api:auth:apitoken:apitoken-detail', args=(token_id,)))
        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)


class APITokenSecurityTestCase(APITestCase):
    def setUp(self):
        self.password = 'abcd1234'
        self.user_bob = User.objects.create_user(
            username='api-token-user-bob',
            password=self.password,
        )
        self.user_alice = User.objects.create_user(
            username='api-token-user-alice',
            password='bcde2345',
        )
        self.token_bob = self.user_bob.apitoken_set.create()
        self.token_alice = self.user_alice.apitoken_set.create()
        self.client.login(username=self.user_bob.username, password=self.password)

    def test_list(self):
        response = self.client.get(reverse('api:auth:apitoken:apitoken-list'))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data['count'], 1)
        self.assertEquals(len(response.data['results']), 1)

    def test_get(self):
        response = self.client.get(reverse('api:auth:apitoken:apitoken-detail', args=(self.token_bob.id,)))
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse('api:auth:apitoken:apitoken-detail', args=(self.token_alice.id,)))
        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch(self):
        response = self.client.patch(
            reverse('api:auth:apitoken:apitoken-detail', args=(self.token_alice.id,)),
            data={'enabled': False}
        )
        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)
