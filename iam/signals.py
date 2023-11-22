import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from iam.models import Group


logger = logging.getLogger(__name__)

User = get_user_model()


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    if created:
        default_group = Group.get_default()
        default_group.membership_set.create(user=instance, role='member')
        logger.debug('Added user %s to the default group.', instance.pk)
