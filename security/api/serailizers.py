from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from django.utils.translation import gettext_lazy as _

from api.apitoken.models import APIToken
from security.models import CommandACL


class CommandACLSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommandACL
        fields = [
            'id', 'token', 'token_name', 'command'
        ]
        read_only_fields = ['id']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['token'].queryset = APIToken.objects.filter(source='api', user=self.context['request'].user, enabled=True)
