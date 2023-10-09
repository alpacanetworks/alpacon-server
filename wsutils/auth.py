import re
import logging

from django.utils.functional import LazyObject
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from channels.auth import AuthMiddleware, UserLazyObject
from channels.middleware import BaseMiddleware
from channels.sessions import CookieMiddleware, SessionMiddleware
from channels.db import database_sync_to_async

from wsutils.models import WebSocketClient
from api.apitoken.models import APIToken


logger = logging.getLogger(__name__)

parser = re.compile('(\w+)[:=] ?"?([a-zA-Z0-9-_]+)"?')


@database_sync_to_async
def get_auth_user(scope):
    for header in scope['headers']:
        if header[0] == b'Authorization' or header[0] == b'authorization':
            auth = header[1].decode('ascii')
            if auth:
                try:
                    data = dict(parser.findall(auth))
                except:
                    continue
                if data.get('id') and data.get('key'):
                    try:
                        return (WebSocketClient.objects.get_valid_client(
                            id=data.get('id'),
                            key=data.get('key')
                        ), 'wsclient')
                    except (ObjectDoesNotExist, ValidationError):
                        logger.debug('Client not found for "%s".', data.get('id', ''))
                        return None
                    except Exception as e:
                        logger.exception(e)
                elif data.get('token'):
                    try:
                        return (APIToken.objects.get_valid_user(key=data.get('token'))[0], 'user')
                    except (ObjectDoesNotExist, ValidationError):
                        logger.debug('Token not found.')
                        return None
                    except Exception as e:
                        logger.exception(e)
    return None


class WebSocketClientLazyObject(LazyObject):
    """
    Throw an error when accessing client object before assignment.
    """
    
    def _setup(self):
        raise ValueError('Accessing scope client before it is ready.')


class APIAuthMiddleware(AuthMiddleware):
    def populate_scope(self, scope):
        super().populate_scope(scope)
        if 'wsclient' not in scope:
            scope['wsclient'] = WebSocketClientLazyObject()

    async def resolve_scope(self, scope):
        result = await get_auth_user(scope)
        if result:
            if result[1] == 'wsclient':
                scope['wsclient']._wrapped = result[0]
            elif result[1] == 'user':
                scope['user']._wrapped = result[0]
            else:
                logger.exception('Not implemented auth type.')
        else:
            scope['wsclient']._wrapped = None
            await super().resolve_scope(scope)

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        self.populate_scope(scope)
        await self.resolve_scope(scope)
        return await self.inner(scope, receive, send)


def APIAuthMiddlewareStack(inner):
    return CookieMiddleware(SessionMiddleware(APIAuthMiddleware(inner)))
