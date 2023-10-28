import logging
from datetime import timedelta

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, PermissionDenied

from background_mail.mail import send_template_mail


RESET_TOKEN_LENGTH = 64
RESET_TOKEN_MAX_SENT_COUNT = 5

logger = logging.getLogger(__name__)

User = get_user_model()


class ResetTokenManager(models.Manager):
    def create_tokens(self, email, request=None):
        users = User.objects.filter(
            email__iexact=email,
            is_active=True,
        )
        tokens = []
        for user in users:
            try:
                token = self.get_queryset().get(
                    user__pk=user.pk,
                    requested_at__gte=timezone.now()-timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT),
                    confirmed_at__isnull=True,
                )
            except ObjectDoesNotExist:
                token = self.model(user=user)
                if request:
                    token.requested_ip = request.META.get('REMOTE_ADDR')
                    token.requested_user_agent = request.META.get('HTTP_USER_AGENT', '')
                token.save()
            except MultipleObjectsReturned:
                logger.error('Multiple reset tokens are found for a user.')
                token = self.get_queryset().filter(
                    user__pk=user.pk,
                    requested_at__gte=timezone.now()-timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT),
                    confirmed_at__isnull=True,
                ).first()
            tokens.append(token)
        return tokens

    def get_valid_token(self, key):
        token = self.get_queryset().get(
            key=key,
            requested_at__gte=timezone.now()-timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT),
            confirmed_at__isnull=True,
        )
        return token

    def delete_expired_tokens(self):
        return self.get_queryset().filter(
            requested_at__lt=timezone.now()-timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT),
            confirmed_at__isnull=True,
        ).delete()


class ResetToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name=_('user')
    )
    key = models.CharField(
        _('key'), max_length=RESET_TOKEN_LENGTH,
        db_index=True, unique=True
    )

    requested_ip = models.GenericIPAddressField(
        _('requested IP'),
        null=True, editable=False,
    )
    requested_user_agent = models.CharField(
        _('requested user agent'), max_length=256,
        default='', editable=False
    )
    requested_at = models.DateTimeField(_('requested at'), auto_now_add=True)

    sent_count = models.PositiveSmallIntegerField(_('sent count'), default=0)
    sent_at = models.DateTimeField(_('sent at'), null=True, editable=False)

    confirmed_ip = models.GenericIPAddressField(
        _('confirmed IP'),
        null=True, editable=False,
    )
    confirmed_user_agent = models.CharField(
        _('confirmed user agent'), max_length=256,
        default='', editable=False
    )
    confirmed_at = models.DateTimeField(_('confirmed at'), null=True, editable=False)

    objects = ResetTokenManager()

    class Meta:
        verbose_name = _('reset token')
        verbose_name_plural = _('reset tokens')

    def __str__(self):
        return self.key

    def get_absolute_url(self):
        return reverse('api:auth:set-password', kwargs={'key': self.key})

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = get_random_string(RESET_TOKEN_LENGTH)
        super().save(*args, **kwargs)

    def send_email(self):
        if self.sent_count >= RESET_TOKEN_MAX_SENT_COUNT:
            raise PermissionDenied(_('Request exceeded your allowance.'))

        send_template_mail(
            _('Reset your password'),
            recipients=[self.user.email],
            template_name='password_reset/password_reset_email',
            context={
                'site_name': getattr(settings, 'SITE_NAME', ''),
                'username': self.user.get_username(),
                'reset_link': settings.REACT_URL + '/auth/reset-password/confirm?token=%s' % self.key,
            },
        )
        self.sent_count += 1
        self.sent_at = timezone.now()
        super().save(update_fields=['sent_count', 'sent_at'])

    def confirm(self, request):
        if self.sent_at is None or self.confirmed_at is not None:
            raise ObjectDoesNotExist

        self.confirmed_at = timezone.now()
        self.confirmed_ip = request.META.get('REMOTE_ADDR')
        self.confirmed_user_agent = request.META.get('HTTP_USER_AGENT')
        super().save(update_fields=['confirmed_at', 'confirmed_ip', 'confirmed_user_agent'])

        # clear all unused tokens
        ResetToken.objects.filter(
            user__pk=self.user.pk,
            confirmed_at__isnull=True
        ).delete()

        # invalidate all login sessions via api tokens
        # all login sessions will be invalidated automatically
        if 'api.apitoken' in settings.INSTALLED_APPS:
            self.user.apitoken_set.filter(source='login').delete()
