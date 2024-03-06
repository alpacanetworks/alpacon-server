"""
WARNING: THIS CODE IS FOR TEST. NOT READY FOR PRODUCTION
"""

import logging
import ldap

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from django_auth_ldap.backend import LDAPBackend

from iam.utils import get_ldap_admin_connection


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populate users from LDAP database'

    def handle(self, *args, **options):
        conn = get_ldap_admin_connection()
        result = conn.search_s(
            settings.LDAP_USER_BASE, ldap.SCOPE_ONELEVEL, attrlist=['uid', 'uidnumber']
        )
        result = sorted(result, key=lambda x: int((x[1]['uidNumber'][0]).decode()))
        for entry in result:
            username = entry[1]['uid'][0].decode()
            logger.info('Synchronizing user %s', username)
            user = LDAPBackend().populate_user(username)
            user.is_ldap_user = True
            user.save(update_fields=['is_ldap_user'])
        conn.unbind_s()
