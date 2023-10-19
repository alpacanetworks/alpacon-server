import logging

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError

from utils.api.viewsets import CreateListRetrieveViewSet
from servers.models import Server


logger = logging.getLogger(__name__)


class ServerObjectMixin:
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if hasattr(request, 'client'):
            request.server = get_object_or_404(Server, pk=self.request.client.pk)

    def get_queryset(self):
        queryset = super().get_queryset()
        if hasattr(self.request, 'client'):
            return queryset.filter(server__pk=self.request.client.pk)
        else:
            if not (self.request.user.is_staff or self.request.user.is_superuser):
                queryset = queryset.filter(
                    server__groups__membership__user__pk=self.request.user.pk
                ).distinct()
            return queryset


class ServerDataViewSet(ServerObjectMixin, CreateListRetrieveViewSet):
    def perform_create(self, serializer):
        if hasattr(self.request, 'server'):
            serializer.save(server=self.request.server)
        else:
            raise ValidationError(_('Server not identified.'))


class ServerMultiDataViewSet(ServerObjectMixin, CreateListRetrieveViewSet):
    def perform_create(self, serializer):
        if hasattr(self.request, 'server'):
            self.get_queryset().delete()
            serializer.save(server=self.request.server)
        else:
            raise ValidationError(_('Server not identified.'))
