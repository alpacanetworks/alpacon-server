from django.contrib.auth import get_user_model

from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication

from api.apitoken.models import APIToken
from api.apitoken.serializers import *
from api.apitoken.auth import APITokenAuthentication
from utils.api.viewsets import DestroyListRetrieveViewSet


User = get_user_model()


class LoginSessionViewSet(DestroyListRetrieveViewSet):
    """
    This interface is to manage login sessions for users. You can list, get, or delete your tokens here. Use `DELETE` to revoke an open session.
    """

    queryset = APIToken.objects.filter(source='login').order_by('-updated_at')
    serializer_class = LoginSessionSerializer
    authentication_classes = [SessionAuthentication, APITokenAuthentication]
    filterset_fields = ['enabled', 'remote_ip']
    search_fields = ['id', 'user_agent', 'remote_ip']

    def get_queryset(self):
        return super().get_queryset().filter(
            user__pk=self.request.user.pk
        ).order_by('-updated_at')


class APITokenViewSet(viewsets.ModelViewSet):
    """
    This interface is to manage API tokens for users. You can list, get, create, patch, or delete your tokens here.

    POST: create new API token
    PATCH: patch the expiration time or enabled status
    DELETE: revoke existing token
    """

    queryset = APIToken.objects.filter(source='api').order_by('-updated_at')
    serializer_class = APITokenSerializer
    authentication_classes = [SessionAuthentication, APITokenAuthentication]
    filterset_fields = ['enabled', 'remote_ip']
    search_fields = ['id', 'user_agent', 'remote_ip']

    def get_serializer_class(self):
        if self.action == 'create':
            return APITokenCreateSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return super().get_queryset().filter(
            user__pk=self.request.user.pk
        ).order_by('-updated_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
