from django.urls import path

from api.password_reset.views import *


urlpatterns = [
    path('', PasswordResetView.as_view(), name='reset-password'),
    path('confirm/<str:key>/', PasswordSetView.as_view(), name='set-password'),
]
