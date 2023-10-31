import uuid

from django.db import models
from django.contrib.auth import password_validation
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.hashers import (
    check_password, is_password_usable, make_password,
)
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist

from api.validators import validate_future


class APIClientManager(models.Manager):
    def create_api_client(self, owner, id=None, key=None, **extra_fields):
        obj = self.model(id=id, owner=owner, **extra_fields)
        if not key:
            key = self.model.make_random_key()
        obj.set_key(key)
        obj.save()
        return (obj, key)

    def get_valid_client(self, id, key):
        obj = self.get_queryset().get(id=id, enabled=True)
        if obj.check_key(key):
            return obj
        else:
            raise ObjectDoesNotExist


class AbstractAPIClient(models.Model):
    """
    An abstract base class for implementing API clients.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        verbose_name=_('ID')
    )
    key = models.CharField(
        max_length=128,
        verbose_name=_('access key')
    )
    ip = models.GenericIPAddressField(
        null=True, blank=True,
        verbose_name=_('IP address'),
        help_text=_('Limit the IP address to access API. Leave it empty to allow any IP address.')
    )
    concurrent = models.BooleanField(
        default=False,
        verbose_name=_('concurrent sessions'),
        help_text=_('Enable this field to allow concurrent sessions for a client at a time.')
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name=_('owner'),
    )
    enabled = models.BooleanField(
        _('enabled'),
        default=True,
        help_text=_('Enable this API client.')
    )
    added_at = models.DateTimeField(_('added at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    expires_at = models.DateTimeField(
        _('expires at'),
        null=True, blank=True,
        validators=[validate_future],
        help_text=_('Token will be expired after this time.')
    )

    objects = APIClientManager()

    _key = None

    class Meta:
        verbose_name = _('API client')
        verbose_name_plural = _('API clients')
        abstract = True

    def __str__(self):
        return '%s' % self.id

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self._key is not None:
            password_validation.password_changed(self._key, self)
            self._key = None

    @classmethod
    def make_random_key(cls, length=32,
                        allowed_chars='abcdefghjkmnpqrstuvwxyz'
                                      'ABCDEFGHJKLMNPQRSTUVWXYZ'
                                      '23456789'):
        '''
        Generate a random key with the given length and given
        allowed_chars. The default value of allowed_chars does not have "I" or
        "O" or letters and digits that look similar -- just to avoid confusion.
        '''
        return get_random_string(length, allowed_chars)

    def set_key(self, raw_key):
        self.key = make_password(raw_key)
        self._key = raw_key

    def check_key(self, raw_key):
        '''
        Return a boolean of whether the raw_key was correct. Handles
        hashing formats behind the scenes.
        '''
        def setter(raw_key):
            self.set_key(raw_key)
            # Key hash upgrades shouldn't be considered key changes.
            self._key = None
            self.save(update_fields=['key'])
        return check_password(raw_key, self.key, setter)

    def set_unusable_key(self):
        # Set a value that will never be a valid hash
        self.key = make_password(None)

    def has_usable_key(self):
        '''
        Return False if set_unusable_key() has been called for this client.
        '''
        return is_password_usable(self.key)
    
    @property
    def owner_name(self):
        return str(self.owner)


class APIClient(AbstractAPIClient):
    """
    API client model to authenticate client machines. Should use `set_key()`
    to store API passwords safe.
    """

    class Meta(AbstractAPIClient.Meta):
        pass


class APIClientUser(AnonymousUser):
    """
    A wrapper class for API clients to make it compatible with 
    Django's authentication system.
    """

    def __init__(self, client):
        self.client = client

    @property
    def is_authenticated(self):
        return True
