from django.conf import settings

from rest_framework.decorators import api_view, permission_classes
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework import permissions


@api_view(['GET'])
@permission_classes((permissions.AllowAny, ))
def api_index(request, format=None):
    api = {}
    for app in settings.REST_API_APPS:
        api[app] = reverse('api:%s:api-root' % app, request=request, format=format)
    if 'api.api_auth' in settings.INSTALLED_APPS:
        api['auth'] = reverse('api:auth:api-root', request=request, format=format)
    api['status'] = reverse('api:status', request=request, format=format)
    return Response(api)


@api_view(['GET'])
@permission_classes((permissions.IsAuthenticated,))
def status(request, format=None):
    return Response({'status': 'Good'})
