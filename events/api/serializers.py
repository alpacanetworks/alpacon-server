from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from api.apitoken.models import APIToken
from events.models import Event, Command
from security.models import CommandACL
from websh.mixins import WebshValidationSerializer


class EventSerializer(serializers.ModelSerializer):
    repeated = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
        label=_('Repeated'),
        help_text=_('Check this field if this event is occurring repeatedly.')
    )
    class Meta:
        model = Event
        fields = ['server', 'record', 'count', 'reporter', 'description', 'data', 'repeated']
        read_only_fields = ['count']

    def save(self, server):
        if self.validated_data['repeated']:
            try:
                with transaction.atomic():
                    obj = Event.objects.select_for_update(of=('self',)).filter(
                        server__pk=server.pk,
                        record=self.validated_data['record'],
                        reporter=self.validated_data['reporter'],
                        updated_at__gt=timezone.now()-timedelta(minutes=10),
                    ).latest()
                    obj.count += 1
                    obj.save(update_fields=['count', 'updated_at'])
                return obj
            except ObjectDoesNotExist:
                pass
        del self.validated_data['repeated']
        obj = Event.objects.create(server=server, **self.validated_data)
        obj.handle_event()
        return obj


class EventListSerializer(EventSerializer):
    class Meta:
        model = Event
        fields = ['server', 'record', 'count', 'reporter', 'description']


class CommandSerializer(serializers.ModelSerializer):
    scheduled_at = serializers.DateTimeField(
        required=False, allow_null=True,
        label=_('Scheduled at')
    )

    class Meta:
        model = Command
        fields = [
            'id', 'shell', 'line', 'data', 'success', 'result',
            'status', 'response_delay', 'elapsed_time',
            'added_at', 'scheduled_at', 'delivered_at', 'acked_at', 'handled_at',
            'server', 'server_name', 'requested_by', 'requested_by_name', 'run_after'
        ]
        read_only_fields = ['id']


class CommandListSerializer(CommandSerializer):
    class Meta:
        model = Command
        fields = [
            'id', 'shell', 'line', 'success', 'result', 'status',
            'response_delay', 'elapsed_time', 'added_at', 'server',
            'server_name', 'username', 'groupname', 'requested_by', 'requested_by_name',
        ]


class CommandCreateSerializer(WebshValidationSerializer, CommandSerializer):
    class Meta(CommandSerializer.Meta):
        fields = [
            'id', 'shell', 'line', 'data', 'username', 'groupname',
            'added_at', 'scheduled_at', 'server', 'requested_by', 'run_after'
        ]

    def validate_scheduled_at(self, value):
        if value is None:
            value = timezone.now()
        return value

    def validate_line(self, value):
        auth = self.context['request'].auth
        if isinstance(auth, APIToken) and auth.source == 'api':
            if not CommandACL.is_allowed(command=value, token=auth):
                raise ValidationError(_('Permission denied'))
        return value

class CommandUpdateSerializer(CommandSerializer):
    class Meta(CommandSerializer.Meta):
        fields = [
            'success', 'result', 'elapsed_time', 'acked_at', 'handled_at'
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'result': {'write_only': True},
        }

    def validate_acked_at(self, value):
        if self.instance.acked_at is not None:
            raise ValidationError(_('Command has been already acknowledged.'))
        return timezone.now()

    def validate_handled_at(self, value):
        if self.instance.handled_at is not None:
            raise ValidationError(_('Command has been already handled.'))
        return timezone.now()

    def validate(self, attrs):
        if 'handled_at' in attrs:
            return attrs
        elif 'acked_at' in attrs:
            return {
                'acked_at': attrs['acked_at']
            }
        elif 'result' in attrs:
            if self.instance.handled_at is not None:
                raise ValidationError(_('Command has been already handled.'))
            return {
                'result': attrs['result']
            }
        else:
            raise ValidationError(
                _('You should set at lease one of `result`, `acked_at`, and `handled_at`.')
            )


class CommandResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Command
        fields = ['success', 'result']
