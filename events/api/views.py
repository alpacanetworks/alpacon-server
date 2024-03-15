import logging

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from events.models import Event, Command
from events.api.serializers import (
    EventSerializer, EventListSerializer,
    CommandSerializer, CommandListSerializer,
    CommandCreateSerializer, CommandUpdateSerializer, CommandResultSerializer
)
from servers.api.mixins import ServerObjectMixin, ServerDataViewSet


logger = logging.getLogger(__name__)


class EventViewSet(ServerDataViewSet):
    queryset = Event.objects.order_by('-added_at')
    serializer_class = EventSerializer
    filterset_fields = ['server', 'reporter']
    search_fields = ['server__id', 'server__name', 'reporter', 'record', 'description']

    def get_serializer_class(self):
        if self.action == 'list':
            return EventListSerializer
        else:
            return super().get_serializer_class()


class CommandViewSet(ServerObjectMixin, viewsets.ModelViewSet):
    queryset = Command.objects.all()
    serializer_class = CommandSerializer
    filterset_fields = ['server', 'requested_by']
    search_fields = [
        'server__id', 'server__name', 'line', 'result',
        'requested_by__username', 'requested_by__first_name', 'requested_by__last_name'
    ]
    ordering = ['-scheduled_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        if not hasattr(self.request, 'client'):
            queryset = queryset.exclude(
                Q(shell='internal')
                & (
                    ((Q(line='ping') | Q(line='debug')) & Q(requested_by__isnull=True))
                    | Q(line='resizepty')
                )
            )
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return CommandListSerializer
        elif self.action == 'create':
            return CommandCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return CommandUpdateSerializer
        else:
            return super().get_serializer_class()

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)
        if (
            serializer.instance.scheduled_at <= timezone.now()
            and serializer.instance.server.is_connected
        ):
            serializer.instance.execute()

    def perform_destroy(self, instance):
        if instance.delivered_at is not None:
            raise ValidationError({
                'non_field_errors': [
                    _('Command cannot be cancelled as it has already been sent to the server.')
                ]
            })
        return super().perform_destroy(instance)
