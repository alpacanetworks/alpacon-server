'''
ASGI entrypoint. Configures Django and then runs the application
defined in the ASGI_APPLICATION setting.
'''

import os

from django.core.asgi import get_asgi_application

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alpacon.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

from wsutils.auth import APIAuthMiddlewareStack
from servers.routing import websocket_urlpatterns as servers_urlpatterns
from websh.routing import websocket_urlpatterns as websh_urlpatterns


application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        APIAuthMiddlewareStack(
            URLRouter(
                servers_urlpatterns
                + websh_urlpatterns
            )
        )
    ),
})
