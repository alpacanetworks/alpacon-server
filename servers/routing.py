from django.urls import path

from servers.consumer import BackhaulConsumer


websocket_urlpatterns = [
    path('ws/servers/backhaul/', BackhaulConsumer.as_asgi()),
]
