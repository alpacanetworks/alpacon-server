import uuid
from datetime import timedelta

from django.db import models
from django.db.models import Q, UniqueConstraint
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from api.validators import validate_future


class APITokenManager(models.Manager):
    def create_via_login(self, user, request):
        return self.create(
            user=user,
            source='login',
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            remote_ip=request.META.get('REMOTE_ADDR', None),
            expires_at=timezone.now()+timedelta(days=settings.LOGIN_VALID_DAYS)
        )

    def get_valid_user(self, key):
        token = self.get_queryset().only('user').get(
            Q(key=key)
            & Q(enabled=True)
            & Q(user__is_active=True)
            & (Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
        )
        return (token.user, token)

    def delete_token(self, user, key):
        return self.get_queryset().filter(
            user__pk=user.pk,
            key=key,
        ).delete()

    def delete_expired_tokens(self):
        return self.get_queryset().filter(expires_at__lt=timezone.now()).delete()


class APIToken(models.Model):
    SOURCES = [
        ('login', _('Browser login')),
        ('api', _('API registration')),
    ]
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        verbose_name=_('ID')
    )
    name = models.CharField(
        _('name'),
        max_length=128, default='', blank=True,
        help_text=_('Name your token so that you can identify it easily.')
    )
    key = models.CharField(
        _('key'),
        max_length=128, blank=True,
        unique=True,
    )
    enabled = models.BooleanField(
        _('enabled'),
        default=True,
        help_text=_('Enable access using this token.')
    )
    source = models.CharField(
        _('source'),
        max_length=8,
        choices=SOURCES, default='api',
        editable=False,
    )
    user_agent = models.CharField(
        _('user agent'), max_length=256,
        default='', editable=False,
    )
    remote_ip = models.GenericIPAddressField(
        _('remote IP'),
        null=True, editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        editable=False,
        verbose_name=_('user')
    )
    added_at = models.DateTimeField(_('added at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    expires_at = models.DateTimeField(
        _('expires at'),
        null=True, blank=True,
        validators=[validate_future],
        help_text=_('Token will be expired after this time.')
    )

    objects = APITokenManager()

    class Meta:
        verbose_name = _('API token')
        verbose_name_plural = _('API tokens')
        constraints = [
            UniqueConstraint(fields=['name', 'user'], condition=Q(source='api'), name='unique_api_token')
        ]

    def __str__(self):
        return str(self.name)

    def clean_expires_at(self):
        if self.expires_at < timezone.now():
            raise ValidationError(_('Valid through must be a future time.'))
        return self.expires_at

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = get_random_string(64)
        super().save(*args, **kwargs)

