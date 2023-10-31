from django.http import Http404
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from api.api_auth.serializers import NewPasswordSerializer
from api.password_reset.serializers import PasswordResetSerializer
from api.password_reset.models import ResetToken


class PasswordResetView(GenericAPIView):
    """
    Reset password if user forgot it. We will email the user with a password reset link. User can reset the password by clicking the reset link we've sent.
    """

    serializer_class = PasswordResetSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = ResetToken.objects.create_tokens(serializer.validated_data['email'], request)
        for obj in tokens:
            obj.send_email()
        return Response({
            'details': _('Please check the email.')
        }, status=status.HTTP_200_OK)


class PasswordSetView(GenericAPIView):
    """
    Users can reset their password by using the link provided via email.
    """

    serializer_class = NewPasswordSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'key'

    def get_object(self):
        return ResetToken.objects.get_valid_token(
            key=self.request.parser_context['kwargs']['key']
        )

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except ObjectDoesNotExist:
            raise Http404()
        return Response(status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except ObjectDoesNotExist:
            raise Http404()
        serializer = self.get_serializer(
            instance=self.object.user,
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        self.object.confirm(request)
        serializer.save()
        return Response(
            {'detail': _('Your password has been changed successfully.')},
            status=status.HTTP_200_OK
        )
