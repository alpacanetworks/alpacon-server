from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.apiclient.models import APIClient
from api.apiclient.tokens import JWTRefreshToken


class JWTLoginSerializer(serializers.Serializer):
    """
    After authenticating whether it is a valid API client using the ID and Key received through the request, the access token and refresh token are returned using the client_id.
    """

    id = serializers.UUIDField(
        label=_('ID'),
        write_only=True,
    )
    key = serializers.CharField(
        max_length=128,
        label=_('key'),
        style={'input_type': 'password'},
        write_only=True,
    )

    def validate(self, data):
        client_id = data['id']
        client_key = data['key']
        obj = APIClient.objects.get_valid_client(id=client_id, key=client_key)
        if obj is not None:
            refresh = JWTRefreshToken.for_client(client_id)
            return {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        else:
            raise ValidationError(_('Login credentials are incorrect.'), 'credential-error')


class JWTRefreshSerializer(serializers.Serializer):
    """
    After verifying whether the refresh token received in the request is a valid token, a new access token is returned.
    """

    refresh = serializers.CharField()
    access = serializers.CharField(read_only=True)
    token_class = JWTRefreshToken

    def validate(self, data):
        refresh = self.token_class(data['refresh'])
        return {
            'access': str(refresh.access_token)
        }
