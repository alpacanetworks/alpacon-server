from django.urls import path

from websh.consumer import *


websocket_urlpatterns = [
    path('ws/websh/pty/<uuid:pk>/<str:token>/', PtyConsumer.as_asgi()),
    path('ws/websh/<uuid:pk>/<str:token>/', WebshConsumer.as_asgi()),
]