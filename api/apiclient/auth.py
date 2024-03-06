import re
import logging

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import Token
from rest_framework_simplejwt.exceptions import InvalidToken

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
        

class APIClientJWTAuthentication(JWTAuthentication):
    """
    An authentication plugin that authenticates requests through a JSON web token provided in a request header.
    """

    client_model = APIClient

    def authenticate(self, request: Request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        request.client = self.get_client(validated_token)
        return (APIClientUser(request.client), validated_token)
    
    def get_client(self, validated_token: Token):
        """
        Attempts to find and return a client using the given validated token.
        """
        
        try:
            client_id = validated_token[settings.SIMPLE_JWT['CLIENT_ID_CLAIM']]
        except KeyError:
            raise InvalidToken(_('Token contained no recognizable user identification'))
        try:
            client = self.client_model.objects.get(**{settings.SIMPLE_JWT['CLIENT_ID_FIELD']: client_id})
        except self.client_model.DoesNotExist:
            raise AuthenticationFailed(_('Client not found'), code='client_not_found')
        return client
