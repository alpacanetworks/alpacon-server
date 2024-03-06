import re
import logging

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.translation import gettext_lazy as _

from rest_framework.authentication import BaseAuthentication

from api.apitoken.models import APIToken


logger = logging.getLogger(__name__)

parser = re.compile('(\w+)[:=] ?"?([a-zA-Z0-9-_]+)"?')


def get_auth_token(request):
    auth = request.headers.get('authorization')
    if not auth:
        return None

    try:
        data = dict(parser.findall(auth))
    except Exception as e:
        logger.exception(e)
        return None

    token = data.get('token', '')
    if not token:
        return None
    return token


class APITokenAuthentication(BaseAuthentication):
    model = None

    def authenticate(self, request):
        token = get_auth_token(request)
        if not token:
            return None
        try:
            return APIToken.objects.get_valid_user(key=token)
        except (ObjectDoesNotExist, ValidationError):
            logger.debug('Token not found.')
            return None
        except Exception as e:
            logger.exception(e)
            return None
