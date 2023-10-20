import os

from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from websh.models import Session, UploadedFile, DownloadedFile, Channel, UserChannel, PtyChannel
from servers.api.serializers import RelatedServerField


class SessionSerializer(serializers.ModelSerializer):
    server = RelatedServerField()

    class Meta:
        model = Session
        fields = ['id', 'rows', 'cols', 'server', 'server_name',
                  'user', 'user_name', 'root', 'user_agent', 'remote_ip',
                  'record', 'added_at', 'updated_at', 'closed_at']
        read_only_fields = ['id', 'record']


class SessionListSerializer(SessionSerializer):
    class Meta:
        model = Session
        fields = ['id', 'server', 'server_name', 'user', 'user_name',
                  'root', 'user_agent', 'remote_ip', 'added_at', 'closed_at']


class SessionCreateSerializer(SessionSerializer):
    websocket_url = serializers.CharField(
        read_only=True,
        label=_('WebSocket URL')
    )

    class Meta(SessionSerializer.Meta):
        fields = ['id', 'rows', 'cols', 'server', 'user', 'root', 'user_agent', 'remote_ip', 'websocket_url']

    def validate_root(self, val):
        if val and not (self.context['request'].user.is_staff or self.context['request'].user.is_superuser):
            raise ValidationError(_('Only superuser or staff can access this server as root.'))
        return val

    def create(self, validated_data):
        instance = super().create(validated_data)
        user_channel = UserChannel.objects.create(session=instance, is_master=True, read_only=False)

        instance.websocket_url = (
                ('wss://' if self.context['request'].is_secure() else 'ws://')
                + self.context['request'].get_host()
                + user_channel.get_user_ws_url()
        )
        return instance


class SessionUpdateSerializer(SessionSerializer):
    class Meta(SessionSerializer.Meta):
        fields = ['rows', 'cols']

    def validate(self, attrs):
        if self.instance.closed_at is not None:
            raise ValidationError(_('Closed sessions cannot be updated.'))
        return super().validate(attrs)


class SessionShareSerializer(SessionSerializer):
    read_only = serializers.BooleanField(
        label=_('Read only'),
        help_text=_('For read-only sessions, the invitee cannot type any characters to the terminal.')
    )

    class Meta(SessionSerializer.Meta):
        fields = ['read_only']


class SessionJoinSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        label=_('Password'),
        style={'input_type': 'password'}
    )

    class Meta:
        model = Session
        fields = ['password']

    def validate(self, attrs):
        attrs = super().validate(attrs)

        try:
            user_channel = UserChannel.objects.get(
                session=self.instance,
                password=attrs['password'],
                token_expired_at__gt=timezone.now(),
            )
        except UserChannel.DoesNotExist:
            raise ValidationError(_('Password does not match or session has expired.'))
        except UserChannel.MultipleObjectsReturned:
            raise ValidationError(_('Unkown error'))

        if self.context['request'].user.is_authenticated:
            user_channel.user = self.context['request'].user
            user_channel.save(update_fields=['user'])

        return {
            'websocket_url': (
                ('wss://' if self.context['request'].is_secure() else 'ws://')
                + self.context['request'].get_host()
                + user_channel.get_user_ws_url()
            ),
            'server': str(self.instance.server),
            'read_only': user_channel.read_only,
            'rows': self.instance.rows,
            'cols': self.instance.cols,
        }


class UploadedFileSerializer(serializers.ModelSerializer):
    server = RelatedServerField()
    download_url = serializers.URLField(source='get_download_url', read_only=True)

    class Meta:
        model = UploadedFile
        fields = ['id', 'name', 'path', 'content', 'size', 'server', 'user', 'expires_at', 'download_url']
        read_only_fields = ['id', 'expires_at', 'download_url']
        extra_kwargs = {
            'content': {
                'write_only': True,
            },
        }


class DownloadedFileSerializer(serializers.ModelSerializer):
    server = RelatedServerField()
    upload_url = serializers.URLField(source='get_upload_url', read_only=True)
    download_url = serializers.URLField(source='get_download_url', read_only=True)

    class Meta:
        model = DownloadedFile
        fields = ['id', 'name', 'path', 'size', 'server', 'user', 'expires_at', 'upload_url', 'download_url']
        read_only_fields = ['id', 'expires_at', 'upload_url', 'download_url']

    def create(self, validated_data):
        validated_data['name'] = os.path.basename(validated_data['path'])
        return DownloadedFile.objects.create(**validated_data)


class DownloadedFileUploadSerializer(DownloadedFileSerializer):
    class Meta(DownloadedFileSerializer.Meta):
        fields = ['content']
        extra_kwargs = {
            'content': {
                'write_only': True,
            },
        }
