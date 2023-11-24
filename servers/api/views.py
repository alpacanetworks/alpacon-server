import logging

from django.http.response import FileResponse
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import SessionAuthentication

from api.apitoken.auth import APITokenAuthentication

from servers.models import Server, Installer, Note
from servers.api.serializers import (
    ServerSerializer, ServerListSerializer, ServerCreateSerializer,
    ServerMetaSerializer, ServerActionSerializer, ServerStarStatusSerializer,
    InstallerSerializer, NoteSerializer, NoteCreateSerializer
)
from servers.api.permissions import ServerObjectPermission, NoteObjectPermission
from events.api.serializers import CommandSerializer
from proc.api.serializers import (
    SystemInfoSerializer, OsVersionSerializer, SystemTimeSerializer,
    SystemUserSerializer, SystemGroupSerializer, InterfaceSerializer, SystemPackageSerializer
)


logger = logging.getLogger(__name__)


class ServerViewSet(viewsets.ModelViewSet):
    queryset = Server.objects.all()
    serializer_class = ServerSerializer
    filterset_fields = ['name', 'version', 'enabled', 'commissioned', 'owner', 'groups']
    search_fields = [
        'id', 'name', 'version', 'session__remote_ip',
        'owner__username', 'owner__first_name', 'owner__last_name', 'groups__name'
    ]
    ordering_fields = ['name', 'commissioned', 'version', 'osquery_version', 'load', 'started_at', 'owner']
    ordering = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        if hasattr(self.request, 'client'):
            return queryset.filter(pk=self.request.client.pk)
        else:
            if not (self.request.user.is_staff or self.request.user.is_superuser):
                queryset = queryset.filter(
                    groups__membership__user__pk=self.request.user.pk
                ).distinct()

            if self.request.query_params.get('starred', None) == 'true':
                return queryset.filter(
                    starredserver__user__pk=self.request.user.pk,
                ).order_by('starredserver__ordering')
            elif self.request.query_params.get('starred', None) == 'false':
                return queryset.exclude(
                    starredserver__user__pk=self.request.user.pk,
                )
            else:
                return queryset

    def get_object(self):
        if self.kwargs['pk'] == '-' and hasattr(self.request, 'client'):
            return Server.objects.get(pk=self.request.client.pk)
        else:
            return super().get_object()

    def get_serializer_class(self):
        if self.action == 'create':
            return ServerCreateSerializer
        elif self.action == 'list':
            return ServerListSerializer
        else:
            return super().get_serializer_class()

    def get_serializer(self, *args, **kwargs):
        if self.action in ['list', 'retrieve', 'update', 'partial_update', 'actions', 'star']:
            return super().get_serializer(user=self.request.user, *args, **kwargs)
        else:
            return super().get_serializer(*args, **kwargs)

    # def list(self, request, *args, **kwargs):
    #     response = super().list(request, *args, **kwargs)
    #     response.data = sorted(
    #         response.data,
    #         key=lambda x: x['starred'] if x['starred'] else 9,
    #     )
    #     return response

    def create(self, request, *args, **kwargs):
        if hasattr(request, 'client'):
            return Response(data={
                'non_field_errors': [_('This action is not for alpamon.')]
            }, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['put'], serializer_class=ServerMetaSerializer)
    def commit(self, request, pk=None):
        if not hasattr(request, 'client'):
            return Response(data={
                'non_field_errors': [_('This action is only for alpamon.')]
            }, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(instance=self.get_object(), data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], serializer_class=ServerActionSerializer)
    def actions(self, request, pk=None):
        serializer = self.get_serializer(instance=self.get_object(), data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            data=CommandSerializer(instance=serializer.command).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get', 'post'], serializer_class=ServerStarStatusSerializer, permission_classes=[IsAuthenticated])
    def star(self, request, pk=None):
        self.object = self.get_object()
        try:
            instance = self.object.starredserver_set.get(
                user__pk=request.user.pk
            )
        except ObjectDoesNotExist:
            instance = None

        if request.method == 'POST':
            serializer = self.get_serializer(
                instance=instance,
                data=request.data,
                context={'server': self.get_object()}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
        else:
            serializer = self.get_serializer(
                instance=instance,
                context={'server': self.get_object()}
            )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], serializer_class=SystemInfoSerializer)
    def info(self, request, pk=None):
        serializer = self.get_serializer(
            instance=self.get_object().systeminfo_set.latest()
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], serializer_class=OsVersionSerializer)
    def os(self, request, pk=None):
        serializer = self.get_serializer(
            instance=self.get_object().osversion_set.latest()
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], serializer_class=SystemTimeSerializer)
    def time(self, request, pk=None):
        serializer = self.get_serializer(
            instance=self.get_object().systemtime_set.latest()
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], serializer_class=SystemUserSerializer)
    def users(self, request, pk=None):
        serializer = self.get_serializer(
            instance=self.get_object().systemuser_set.filter(
                iam_user__isnull=False
            ).order_by('uid'),
            many=True,
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], serializer_class=SystemGroupSerializer)
    def groups(self, request, pk=None):
        serializer = self.get_serializer(
            instance=self.get_object().systemgroup_set.filter(
                iam_group__isnull=False,
            ).order_by('gid'),
            many=True,
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], serializer_class=InterfaceSerializer)
    def interfaces(self, request, pk=None):
        serializer = self.get_serializer(
            instance=self.get_object().interface_set.exclude(
                address__isnull=True
            ).order_by('name'),
            many=True,
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], serializer_class=SystemPackageSerializer)
    def packages(self, request, pk=None):
        serializer = self.get_serializer(
            instance=self.get_object().systempackage_set.all(),
            many=True,
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class RetrieveInstallerView(RetrieveAPIView):
    queryset = Installer.objects.all()
    serializer_class = InstallerSerializer
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return FileResponse(
            self.object.content,
            filename='installer.sh',
            as_attachment=True,
        )


class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    authentication_classes = [SessionAuthentication, APITokenAuthentication]
    permission_classes = [NoteObjectPermission]
    filterset_fields = ['server', 'author', 'private', 'pinned']
    search_fields = [
        'content', 'server__name',
        'author__first_name', 'author__last_name', 'author__username'
    ]
    ordering_fields = ['pinned', 'private', 'added_at', 'updated_at']
    ordering = ['-pinned', '-updated_at']

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            Q(private=False)
            | (Q(private=True) & Q(author__pk=self.request.user.pk))
        )
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(
                Q(server__groups__membership__user__pk=self.request.user.pk)
                | Q(server__owner__pk=self.request.user.pk)
            ).distinct()
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return NoteCreateSerializer
        else:
            return super().get_serializer_class()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
