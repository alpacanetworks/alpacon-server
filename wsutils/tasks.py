from datetime import timedelta

from django.utils import timezone
from django.db import transaction

from celery import shared_task

from wsutils.models import WebSocketSession


@shared_task(ignore_results=True, queue='watchdog')
def clear_stale_sessions():
    sessions = WebSocketSession.objects.select_for_update(of=('self',)).filter(
        updated_at__lt=timezone.now()-timedelta(minutes=15),
        deleted_at__isnull=True,
    )

    with transaction.atomic():
        for session in sessions:
            session.deleted_at = timezone.now()
            session.save(update_fields=['deleted_at'])

    for session in sessions:
        session.close(quit=False)

    return len(sessions)


@shared_task(ignore_results=True, queue='cleanup')
def delete_old_sessions():
    return WebSocketSession.objects.filter(
        deleted_at__lt=timezone.now()-timedelta(weeks=1),
    ).delete()[0]


@shared_task(ignore_results=True, queue='celery')
def drop_concurrent_sessions(client_pk, session_pk):
    """
    This function drops concurrent sessions for a WebSocketClient
    when new connection comes in. As we need to disconnect sessions one-by-one,
    we update deleted_at field first atomaically, and call close later.
    """
    sessions = WebSocketSession.objects.select_for_update(of=('self',)).filter(
        client__pk=client_pk,
        deleted_at__isnull=True,
    ).exclude(
        pk=session_pk,
    )

    with transaction.atomic():
        for session in sessions:
            session.deleted_at = timezone.now()
            session.save(update_fields=['deleted_at'])

    for session in sessions:
        session.close(quit=True)

    return len(sessions)


@shared_task(ignore_results=True, queue='cleanup')
def delete_session(session_pk):
    """
    delete_session: this function is not in use for now.
    """
    return WebSocketSession.objects.filter(
        pk=session_pk,
        deleted_at__isnull=True,
    ).update(
        deleted_at=timezone.now()
    ) == 1
