from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class APIClientConfig(AppConfig):
    name = 'api.apiclient'
    verbose_name = _('API client')
