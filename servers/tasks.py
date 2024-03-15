import logging
from datetime import timedelta

from django.utils import timezone

from celery import shared_task

from servers.models import Server, Installer


logger = logging.getLogger(__name__)


@shared_task(ignore_result=True, queue='watchdog')
def ping_all_servers():
    for obj in Server.objects.filter(
        enabled=True,
        deleted_at__isnull=True,
    ).exclude(session__isnull=True):
        if obj.is_connected:
            obj.execute('ping')


@shared_task(ignore_result=True, queue='watchdog')
def debug_all_servers():
    for obj in Server.objects.filter(
        enabled=True,
        deleted_at__isnull=True,
    ).exclude(session__isnull=True):
        if obj.is_connected:
            obj.execute('debug')


@shared_task(ignore_result=True, queue='watchdog')
def check_server_status(server_pk=None):
    if server_pk is None:
        for obj in Server.objects.filter(
            enabled=True,
            deleted_at__isnull=True,
        ):
            obj.status = obj.get_current_status()
            obj.save(update_fields=['status'])
    else:
        obj = Server.objects.get(pk=server_pk)
        obj.status = obj.get_current_status()
        obj.save(update_fields=['status'])


@shared_task(ignore_result=True, queue='cleanup')
def cleanup_installers():
    Installer.objects.filter(
        added_at__lt=timezone.now()-timedelta(days=1)
    ).delete()
