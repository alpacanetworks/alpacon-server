import re
import uuid
import logging

from django.db import models
from django.utils.translation import gettext_lazy as _


logger = logging.getLogger(__name__)

regex = re.compile(r'(?P<major>0|[1-9][0-9]*)(\.(?P<minor>0|[1-9][0-9]*))?(\.(?P<patch>0|[1-9][0-9]*))?\-?(?P<label>.*)')


class BaseModel(models.Model):
    added_at = models.DateTimeField(_('added at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    deleted_at = models.DateTimeField(_('deleted at'), null=True, editable=False)

    class Meta:
        abstract = True


class UUIDBaseModel(BaseModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        verbose_name=_('ID')
    )

    class Meta:
        abstract = True


class SemanticVersionedModel(models.Model):
    version = models.CharField(_('version'), max_length=64, blank=True)
    v_major = models.PositiveIntegerField(_('major version'), default=0, editable=False)
    v_minor = models.PositiveIntegerField(_('major version'), default=0, editable=False)
    v_patch = models.PositiveIntegerField(_('major version'), default=0, editable=False)
    v_label = models.CharField(_('version label'), max_length=32, default='', editable=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        try:
            match = regex.match(self.version)
            if match:
                self.v_major = match.group('major') or 0
                self.v_minor = match.group('minor') or 0
                self.v_patch = match.group('patch') or 0
                self.v_label = match.group('label') or ''
        except Exception as e:
            logger.exception(e)
        super().save(*args, **kwargs)
