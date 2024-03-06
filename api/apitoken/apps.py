from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ApitokenConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.apitoken'
    verbose_name = _('API token')
