from django.test import TestCase
from django.http.request import HttpRequest
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.reverse import reverse

from api.password_reset.models import ResetToken, RESET_TOKEN_MAX_SENT_COUNT


User = get_user_model()

UA_STRING = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'


class ResetTokenModelTestCase(TestCase):
    def setUp(self):
        self.username = get_random_string(16)
        self.password = get_random_string(16)
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
        )
        self.request = HttpRequest()
        self.request.META = {
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_USER_AGENT': UA_STRING,
        }

    def test_create(self):
        token = ResetToken.objects.create(user=self.user)
        self.assertTrue(token.key)
        self.assertEquals(token.pk, ResetToken.objects.get(key=token.key).pk)

    def test_create_with_request_info(self):
        ResetToken.objects.create(
            user=self.user,
            requested_ip='1.2.3.4',
            requested_user_agent=UA_STRING,
        )

    def test_get_absolute_url(self):
        token = ResetToken.objects.create(user=self.user)
        self.assertEquals(
            '/api/auth/reset_password/confirm/%(token)s/' % {'token': token.key},
            token.get_absolute_url()
        )

    def test_send_email(self):
        token = ResetToken.objects.create(user=self.user)
        token.send_email()

    def test_send_email_many_times(self):
        token = ResetToken.objects.create(user=self.user)
        for _ in range(RESET_TOKEN_MAX_SENT_COUNT):
            token.send_email()
        with self.assertRaises(PermissionDenied):
            token.send_email()

    def test_confirm_not_sent(self):
        token = ResetToken.objects.create(user=self.user)
        with self.assertRaises(ObjectDoesNotExist):
            token.confirm(self.request)

    def test_confirm_twice(self):
        token = ResetToken.objects.create(user=self.user)
        token.send_email()
        token.confirm(self.request)
        with self.assertRaises(ObjectDoesNotExist):
            token.confirm(self.request)


class ResetTokenManagerTestCase(TestCase):
    def setUp(self):
        self.username = get_random_string(16)
        self.password = get_random_string(16)
        self.email = '%s@test.com' % get_random_string(8)
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email=self.email,
        )
        self.request = HttpRequest()
        self.request.META = {
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_USER_AGENT': UA_STRING,
        }

    def test_create_tokens(self):
        tokens = ResetToken.objects.create_tokens(self.email, self.request)
        for obj in tokens:
            obj.send_email()
            token = ResetToken.objects.get_valid_token(obj.key)
            token.confirm(self.request)


class ResetTokenViewTestCase(APITestCase):
    def setUp(self):
        self.username = get_random_string(16)
        self.password = get_random_string(16)
        self.email = '%s@test.com' % get_random_string(8)
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email=self.email,
        )

    def test_reset_password(self):
        response = self.client.post(
            reverse('api:auth:reset-password'),
            data={'email': self.email}
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
