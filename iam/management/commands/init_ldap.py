"""
WARNING: THIS CODE IS FOR TEST. NOT READY FOR PRODUCTION
"""

import logging
import ldap.modlist

from django.core.management.base import BaseCommand

from alpacon.settings import LDAP_USER_BASE, LDAP_GROUP_BASE
from iam.utils import get_ldap_admin_connection


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Initialize basic LDAP Organizational Units'

    def handle(self, *args, **options):
        conn = get_ldap_admin_connection()

        # Create User OU
        create_ou(conn, LDAP_USER_BASE, 'Users Organizational Unit')
        logger.info("Creating user ou..")

        # Create Group OU
        create_ou(conn, LDAP_GROUP_BASE, 'Groups Organizational Unit')
        logger.info("Creating group ou..")

        conn.unbind_s()

def create_ou(conn, dn, description):
    ou = {
        'objectClass': [b'organizationalUnit'],
        'description': [description.encode()]
    }
    conn.add_s(dn, ldap.modlist.addModlist(ou))
