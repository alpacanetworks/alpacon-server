from django.db import IntegrityError
from django.utils.translation import gettext_lazy as _

from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError

from api.apitoken.auth import APITokenAuthentication
from security.api.permissions import CommandACLObjectPermission
from security.api.serailizers import CommandACLSerializer
from security.models import CommandACL


class CommandACLViewSet(viewsets.ModelViewSet):
    queryset = CommandACL.objects.all()
    serializer_class = CommandACLSerializer
    authentication_classes = [SessionAuthentication, APITokenAuthentication]
    permission_classes = [CommandACLObjectPermission]
    filterset_fields = ['token']
    search_fields = ['id', 'token__name']
    ordering = ['token']

    def get_queryset(self):
        return super().get_queryset().filter(token__user__pk=self.request.user.pk)

    def perform_create(self, serializer):
        try:
            serializer.save()
        except IntegrityError:
            raise ValidationError(_('Command ACL with this token and command already exists.'))

    def perform_update(self, serializer):
        try:
            serializer.save()
        except IntegrityError:
            raise ValidationError(_('Command ACL with this token and command already exists.'))
