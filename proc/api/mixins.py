import logging


logger = logging.getLogger(__name__)


class ServerObjectMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        if hasattr(self.request, 'client'):
            return queryset.filter(server__pk=self.request.client.pk)
        else:
            return queryset
