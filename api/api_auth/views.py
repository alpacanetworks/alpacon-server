import logging

from django.contrib.auth import logout, get_user_model
from django.contrib.auth.signals import user_logged_out
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.auth import update_session_auth_hash

from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication

from api.api_auth.serializers import *
from api.apitoken.auth import APITokenAuthentication
from api.apitoken.models import APIToken


logger = logging.getLogger(__name__)

User = get_user_model()


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_root(request, format=None):
    api = {
        'login': reverse('api:auth:login', request=request, format=format),
        'logout': reverse('api:auth:logout', request=request, format=format),
        'is_authenticated': reverse('api:auth:is-authenticated', request=request, format=format),
        'csrf_token': reverse('api:auth:csrf-token', request=request, format=format),
        'change_password': reverse('api:auth:change-password', request=request, format=format),
        'reset_password': reverse('api:auth:reset-password', request=request, format=format),
        'set_password': reverse('api:auth:set-password', args=('-',), request=request, format=format),
    }
    if 'api.apitoken' in settings.INSTALLED_APPS:
        api['login_sessions'] = reverse('api:auth:apitoken:loginsession-list', request=request, format=format)
        api['api_tokens'] = reverse('api:auth:apitoken:apitoken-list', request=request, format=format)

    return Response(api)


class LoginView(GenericAPIView):
    """
    Login user using `username` and `password`. Returns `token` that can be used in further API requests.

    Remember the token and include it like `Authorization: token="xxx"` in HTTP headers. The returned token will be valid for 14 days from the last access. Upon the expiry date, any further API access will result in 403 Forbidden.
    """

    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer(self, *args, **kwargs):
        kwargs['request'] = self.request
        return LoginSerializer(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return Response({
                'code': 'already-logged-in',
                'errors': _('Already logged in.'),
            }, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data)
        else:
            return Response(serializer.errors, status=status.HTTP_403_FORBIDDEN)


@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request, format=None):
    if request.successful_authenticator.__class__ == APITokenAuthentication and request.auth:
        APIToken.objects.delete_token(request.user, request.auth.key)
        user_logged_out.send(sender=request.user.__class__, request=request, user=request.user)
        return Response({
            'detail': _('Logged out.'),
        }, status=status.HTTP_200_OK)
    else:
        logout(request)
        return Response({
            'detail': _('Logged out.'),
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def is_authenticated(request, format=None):
    """
    Check if the user is authenticated.
    """

    if request.user.is_authenticated:
        return Response(
            data={'authenticated': True},
            status=status.HTTP_200_OK
        )
    else:
        return Response(
             data={'authenticated': False},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
@ensure_csrf_cookie
def get_csrf_token(request, format=None):
    return Response({'detail': _('CSRF token has been set.')})


class PasswordChangeView(GenericAPIView):
    """
    Change password for the user.
    
    Server validates the correctness of current password for security. New password should satisfy the password security requirements. If one of those checks fails, 400 Bad request will be raised and errors will be set.

    After successful change, all open user sessions will be revoked (logged out) automatically. Tokens will be still alive.
    """

    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [SessionAuthentication, APITokenAuthentication]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # preserve user's current login session on session authentication
        if request.successful_authenticator.__class__ == SessionAuthentication:
            update_session_auth_hash(request, self.request.user)

        return Response(
            {'detail': _('Your password has been changed successfully.')},
            status=status.HTTP_200_OK
        )
