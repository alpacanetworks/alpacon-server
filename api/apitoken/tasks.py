import logging

from celery import shared_task

from api.apitoken.models import APIToken

logger = logging.getLogger(__name__)


@shared_task(ignore_result=True, queue='cleanup')
def delete_expired_tokens():
    return APIToken.objects.delete_expired_tokens()
