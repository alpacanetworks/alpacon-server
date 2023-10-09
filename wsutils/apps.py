from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class WsutilsConfig(AppConfig):
    name = 'wsutils'
    verbose_name = _('WebSocket utils')
