import re
import logging

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.translation import gettext_lazy as _

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from api.apiclient.models import APIClient, APIClientUser


logger = logging.getLogger(__name__)

parser = re.compile('(\w+)[:=] ?"?([a-zA-Z0-9-_]+)"?')


class APIClientAuthentication(BaseAuthentication):
    model = None

    def get_model(self):
        if self.model is not None:
            return self.model
        return APIClient

    def authenticate(self, request):
        auth = request.headers.get('authorization')
        if not auth:
            return None

        try:
            data = dict(parser.findall(auth))
        except Exception as e:
            logger.exception(e)
            return None

        try:
            client_id = data.get('id', '')
            client_key = data.get('key', '')
            if not client_id or not client_key:
                return None

            request.client = self.get_model().objects.get_valid_client(
                id=client_id,
                key=client_key
            )
            return (APIClientUser(request.client), None)
        except (ObjectDoesNotExist, ValidationError):
            logger.debug('Client not found.')
            return None
        except Exception as e:
            logger.exception(e)
            return None
