from datetime import timedelta

from django.utils import timezone

from celery import shared_task

from wsutils.models import WebSocketSession


@shared_task(ignore_results=True, queue='watchdog')
def clear_stale_sessions():
    count = 0
    for obj in WebSocketSession.objects.filter(
        updated_at__lt=timezone.now()-timedelta(minutes=15),
        deleted_at__isnull=True,
    ):
        obj.close()
        count += 1
    return count


@shared_task(ignore_results=True, queue='cleanup')
def delete_old_sessions():
    return WebSocketSession.objects.filter(
        deleted_at__lt=timezone.now()-timedelta(weeks=1),
    ).delete()[0]
