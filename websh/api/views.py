import logging

from django.utils import timezone
from django.http.response import FileResponse
from django.db.models import Q

from rest_framework import viewsets, status, permissions, serializers
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.authentication import SessionAuthentication

from api.apitoken.auth import APITokenAuthentication

from utils.api.viewsets import CreateListRetrieveViewSet, CreateUpdateListRetrieveViewSet
from websh.models import Session, UploadedFile, DownloadedFile, UserChannel
from websh.api.serializers import (
    SessionSerializer, SessionListSerializer,
    SessionCreateSerializer, SessionUpdateSerializer,
    SessionJoinSerializer, SessionShareSerializer,
    UploadedFileSerializer, DownloadedFileSerializer, DownloadedFileUploadSerializer,
)
from websh.api.permissions import SessionObjectPermission

logger = logging.getLogger(__name__)


class SessionViewSet(CreateUpdateListRetrieveViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    authentication_classes = [SessionAuthentication, APITokenAuthentication]
    permission_classes = [SessionObjectPermission]
    filterset_fields = ['server', 'user', 'username', 'groupname']
    search_fields = [
        'server__name', 'username', 'groupname',
        'user__first_name', 'user__last_name', 'user__username'
    ]
    ordering = ['-added_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        if not (self.request.user.is_staff or self.request.user.is_superuser) and self.action != 'join':
            queryset = queryset.filter(
                Q(server__groups__membership__user__pk=self.request.user.pk)
                | Q(server__owner__pk=self.request.user.pk)
            ).distinct()
        if self.action in ['update', 'partial_update', 'share']:
            queryset = queryset.filter(
                user__pk=self.request.user.pk,
            )
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return SessionListSerializer
        elif self.action == 'create':
            return SessionCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return SessionUpdateSerializer
        else:
            return super().get_serializer_class()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save()
        serializer.instance.resize_terminal()
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    # Share action returns a shareable URL, allowing users to share the session.
    @action(detail=True, methods=['post'], serializer_class=SessionShareSerializer)
    def share(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        user_channel = UserChannel.objects.create(session=instance, read_only=serializer.validated_data['read_only'])
        shared_url = instance.get_shared_url()
        return Response({
            'shared_url': shared_url,
            'password': user_channel.password,
            'read_only': user_channel.read_only,
            'expiration': user_channel.token_expired_at,
        }, status=status.HTTP_201_CREATED)

    # Join action returns a websocket URL, obtained via the shared_url provided by the share action
    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny], serializer_class=SessionJoinSerializer)
    def join(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return Response(data=serializer.validated_data, status=status.HTTP_201_CREATED)


class ServerQuerySetMixin:
    def get_queryset(self):
        queryset = super().get_queryset().filter(expires_at__gte=timezone.now())
        if hasattr(self.request, 'client'):
            queryset = queryset.filter(server__pk=self.request.client.pk)
        else:
            if not (self.request.user.is_staff or self.request.user.is_superuser):
                queryset = queryset.filter(
                    Q(server__groups__membership__user__pk=self.request.user.pk)
                    | Q(server__owner__pk=self.request.user.pk)
                ).distinct()
        return queryset


class FileDownloadMixin:
    # Client, Alpamon downloads the file by making a GET request to the corresponding URLS
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        self.object = self.get_object()
        if self.object.content:
            try:
                return FileResponse(
                    self.object.content.open('rb'),
                    filename=self.object.name,
                    as_attachment=True,
                )
            except FileNotFoundError:
                raise NotFound('File does not exist.')
        else:
            raise NotFound('File does not exist.')


class UploadedFileViewSet(ServerQuerySetMixin, FileDownloadMixin, CreateListRetrieveViewSet):
    queryset = UploadedFile.objects.all()
    serializer_class = UploadedFileSerializer
    filterset_fields = ['server', 'user', 'username', 'groupname']
    search_fields = [
        'name', 'server__name', 'username', 'groupname',
        'user__first_name', 'user__last_name', 'user__username',
    ]
    ordering = ['-added_at']

    def perform_create(self, serializer):
        obj = serializer.save(user=self.request.user)
        obj.upload()


class DownloadedFileViewSet(ServerQuerySetMixin, FileDownloadMixin, CreateListRetrieveViewSet):
    queryset = DownloadedFile.objects.all()
    serializer_class = DownloadedFileSerializer
    filterset_fields = ['server', 'user', 'username', 'groupname']
    search_fields = [
        'name', 'server__name', 'username', 'groupname',
        'user__first_name', 'user__last_name', 'user__username',
    ]
    ordering = ['-added_at']

    def perform_create(self, serializer):
        obj = serializer.save(user=self.request.user)
        obj.download()

    # Alpamon uploads a file to the URL by making a POST request
    @action(detail=True, methods=['post'], serializer_class=DownloadedFileUploadSerializer)
    def upload(self, request, pk=None):
        serializer = self.get_serializer(instance=self.get_object(), data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_200_OK)
