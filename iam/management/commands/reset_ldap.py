"""
WARNING: THIS CODE IS FOR TEST. NOT READY FOR PRODUCTION
"""

import logging

from django.core.management.base import BaseCommand

from alpacon.local_settings import LDAP_USER_BASE, LDAP_GROUP_BASE
from iam.utils import get_ldap_admin_connection


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Delete basic LDAP Organizational Units'

    def handle(self, *args, **options):
        conn = get_ldap_admin_connection()
        # Delete User OU
        delete_ou(conn, LDAP_USER_BASE)
        logger.info("Deleting user ou..")

        # Delete Group OU
        delete_ou(conn, LDAP_GROUP_BASE)
        logger.info("Deleting group ou..")

        conn.unbind_s()


def delete_ou(conn, dn):
    conn.delete_s(dn)
