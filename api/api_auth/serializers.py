import logging

from django.contrib.auth import get_user_model, authenticate, login
from django.contrib.auth.password_validation import password_validators_help_text_html, validate_password
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.exceptions import ValidationError

from api.apitoken.models import APIToken


logger = logging.getLogger(__name__)

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=150,
        label=_('username'),
        help_text=_(
            'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
        )
    )
    password = serializers.CharField(
        max_length=128,
        label=_('password'),
        style={'input_type': 'password'}
    )
    use_cookie = serializers.BooleanField(
        required=False,
        default=False,
        initial=True,
        label=_('use session cookie'),
        help_text=_('Set this field if you are logging in via the browsable API.')
    )

    def __init__(self, instance=None, data=empty, **kwargs):
        self._request = kwargs.pop('request')
        super().__init__(instance=instance, data=data, **kwargs)

    def validate(self, data):
        use_cookie = data.pop('use_cookie', False)
        user = authenticate(**data)
        if user is not None:
            if use_cookie:
                login(self._request, user)
                return {
                    'success': True,
                }
            else:
                self._request.user = user
                token = APIToken.objects.create_via_login(user, request=self._request)
                user_logged_in.send(User, request=self._request, user=user)
                return {
                    'token': token.key,
                    'expires_at': token.expires_at,
                }
        else:
            user_login_failed.send(
                User,
                credentials={'username': data.get('username', '')},
                request=self._request
            )
            raise ValidationError(_('Login credentials are incorrect.'), 'credential-error')


class CurrentPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(
        max_length=150,
        style={'input_type': 'password'},
        label=_('Current password'),
        help_text=_('Current password is required for account security.')
    )

    def validate_password(self, value):
        if not self.instance.check_password(value):
            raise ValidationError(_('Current password does not match.'), code='wrong_password')
        return value


class NewPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(
        max_length=150,
        style={'input_type': 'password'},
        label=_('New password'),
        help_text=password_validators_help_text_html
    )

    def validate_new_password(self, value):
        validate_password(value, user=self.instance)
        return value

    def save(self, *args, **kwargs):
        self.instance.set_password(self.validated_data['new_password'])
        self.instance.save(update_fields=['password'])


class PasswordChangeSerializer(CurrentPasswordSerializer, NewPasswordSerializer):
    pass
