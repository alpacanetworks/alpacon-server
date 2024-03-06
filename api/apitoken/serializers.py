from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.apitoken.models import APIToken


class LoginSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIToken
        fields = ['id', 'user_agent', 'remote_ip', 'added_at', 'expires_at']


class APITokenSerializer(serializers.ModelSerializer):
    enabled = serializers.BooleanField(
        label=_('Enabled'),
        initial=True, default=True, required=False,
        help_text=_('Enable access using this token.')
    )

    class Meta:
        model = APIToken
        fields = ['id', 'name', 'enabled', 'updated_at', 'expires_at']
        read_only_fields = ['id', 'key']


class APITokenCreateSerializer(APITokenSerializer):
    class Meta(APITokenSerializer.Meta):
        fields = ['id', 'name', 'key', 'enabled', 'updated_at', 'expires_at']
