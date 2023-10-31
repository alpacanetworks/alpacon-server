from django.urls import path, include
from django.conf import settings

from api.views import api_index, status


app_name = 'api'

urlpatterns = [
    path('', api_index, name='index'),
    path('status/', status, name='status'),
    path('apiclient/', include('api.apiclient.urls')),
] + list(map(
    lambda app: path('%s/' % app, include('%s.api.urls' % app)),
    settings.REST_API_APPS
))

if 'api.api_auth' in settings.INSTALLED_APPS:
    urlpatterns.append(path('auth/', include('api.api_auth.urls')))
