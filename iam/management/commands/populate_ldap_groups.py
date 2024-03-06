"""
WARNING: THIS CODE IS FOR TEST. NOT READY FOR PRODUCTION
"""

import logging
import ldap

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from iam.models import Group, Membership, User
from iam.utils import get_ldap_admin_connection


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populate groups from LDAP database'

    def handle(self, *args, **options):
        conn = get_ldap_admin_connection()

        result = conn.search_s(
           settings.LDAP_GROUP_BASE, ldap.SCOPE_ONELEVEL, filterstr='(objectclass=groupofnames)'
        )
        result = sorted(result, key=lambda x: x[1]['cn'][0].decode())

        for entry in result:
            groupname = entry[1]['cn'][0].decode()
            logger.info('Synchronizing group %s', groupname)
            group, _ = Group.objects.get_or_create(
                name=groupname,
                defaults={
                    'display_name': groupname,
                }
            )
            group.is_ldap_group = True
            group.save(update_fields=['is_ldap_group'])

            member_dns = entry[1].get('member', [])
            for member_dn in member_dns:
                decoded_dn = member_dn.decode()
                if decoded_dn.startswith('uid='):
                    dn_parts = decoded_dn.split(',')
                    first_part = dn_parts[0]
                    username = first_part.split('=')[1]
                    user = User.objects.get(username=username)
                    Membership.objects.get_or_create(
                        group=group,
                        user=user,
                        defaults={
                            'role': 'member',
                        }
                    )

        conn.unbind_s()
