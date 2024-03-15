import logging
from datetime import timedelta

from django.utils import timezone
from celery import shared_task

from events.models import Command, Event


logger = logging.getLogger(__name__)


@shared_task(ignore_result=True, queue='cmd')
def execute_scheduled_commands(server_pk=None):
    return Command.execute_all_scheduled(server_pk)


@shared_task(ignore_result=True, queue='cleanup')
def delete_old_events():
    return Event.objects.filter(
        added_at__lt=timezone.now()-timedelta(weeks=1),
    ).delete()


@shared_task(ignore_results=True, queue='cleanup')
def delete_old_commands():
    return Command.objects.filter(
        shell='internal',
        line__in=['ping', 'debug'],
        requested_by__isnull=True,
        scheduled_at__lt=timezone.now()-timedelta(weeks=1),
    ).delete()
