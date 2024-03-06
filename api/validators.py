from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_future(value):
    if value < timezone.now():
        raise ValidationError(
            _('%(time)s must be a future time.'),
            params={'time': value},
            code='invalid-time'
        )
