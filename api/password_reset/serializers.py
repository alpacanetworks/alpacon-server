from django.utils.translation import gettext_lazy as _

from rest_framework import serializers


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(
        max_length=254,
        label=_('Email'),
    )
