import unittest
import ldap3

from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.conf import settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from iam.models import Group
from iam.test_user import get_random_username

User = get_user_model()

"""
WARNING : This test requires a connection to an actual OpenLDAP server. 
          Please specify the appropriate OpenLDAP server URL in AUTH_LDAP_SERVER_URI within your local_settings.py file.
"""


class UserTestMixin:
    def create_user_and_login(self, **kwargs):
        self.password = get_random_string(32)
        self.user = User.objects.create_user(
            username=get_random_username(),
            password=self.password,
            **kwargs
        )
        self.client.login(username=self.user.username, password=self.password)

    def create_ldap_user_via_api(self, **kwargs):
        self.ldap_username = get_random_username()
        self.ldap_password = get_random_string(32)
        self.client.post(reverse('api:iam:user-list'), {
            'username': self.ldap_username,
            'password': self.ldap_password,
            'first_name': get_random_string(8),
            'last_name': get_random_string(8),
            'email': self.ldap_password + '@alpacon.io',
            'is_ldap_user': True,
            **kwargs
        })
        self.ldap_user = User.objects.get(username=self.ldap_username)

    def login(self, username, password):
        response = self.client.post(
            reverse('api:auth:login'), {
                'username': username,
                'password': password,
            }
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertTrue('token' in response.data)
        self.token = response.data['token']
        self.client.credentials(
            HTTP_AUTHORIZATION='token="%s"' % self.token
        )


class GroupTestMixin:
    def create_user_and_login(self, **kwargs):
        self.password = get_random_string(32)
        self.user = User.objects.create_user(
            username=get_random_username(),
            password=self.password,
            **kwargs
        )
        self.client.login(username=self.user.username, password=self.password)

    def create_ldap_group_via_api(self, **kwargs):
        self.groupname = get_random_username()
        self.client.post(reverse('api:iam:group-list'), {
            'name': self.groupname,
            'display_name': get_random_string(32),
            'tags': get_random_string(32),
            'description': get_random_string(128),
            'is_ldap_group': True,
            **kwargs
        })
        self.group = Group.objects.get(name=self.groupname)


class MembershipTestMixin:
    def create_user_and_login(self, **kwargs):
        self.password = get_random_string(32)
        self.user = User.objects.create_user(
            username=get_random_username(),
            password=self.password,
            **kwargs
        )
        self.client.login(username=self.user.username, password=self.password)

    def create_ldap_user_via_api(self, **kwargs):
        self.ldap_username = get_random_username()
        self.ldap_password = get_random_string(32)
        return self.client.post(reverse('api:iam:user-list'), {
            'username': self.ldap_username,
            'password': self.ldap_password,
            'first_name': get_random_string(8),
            'last_name': get_random_string(8),
            'email': self.ldap_password + '@alpacon.io',
            'is_ldap_user': True,
            **kwargs
        })

    def create_ldap_group_via_api(self, **kwargs):
        self.groupname = get_random_username()
        return self.client.post(reverse('api:iam:group-list'), {
            'name': self.groupname,
            'display_name': get_random_string(32),
            'tags': get_random_string(32),
            'description': get_random_string(128),
            'is_ldap_group': True,
            **kwargs
        })

    def create_ldap_user_and_add_member_via_api(self, role):
        response = self.create_ldap_user_via_api()
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('id' in response.data)
        user = response.data

        response = self.client.post(reverse('api:iam:membership-list'), {
            'group': self.group_id,
            'user': user['id'],
            'role': role,
        })
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertEquals(response.data['role'], role)
        return user

    def get_membership_id(self, user_id):
        response = self.client.get(reverse('api:iam:membership-list') + '?group=%(group)s&user=%(user)s' % {
            'group': self.group_id,
            'user': user_id,
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        return str(response.data[0]['id'])


class LDAPTestMixin:
    def connect_ldap_server(self):
        # Connection info for the local OpenLDAP server (could be running in Docker)
        server = ldap3.Server(settings.AUTH_LDAP_SERVER_URI)
        self.conn = ldap3.Connection(server, user=settings.AUTH_LDAP_BIND_DN, password=settings.AUTH_LDAP_BIND_PASSWORD)
        self.conn.bind()

    def create_ldap_ou(self, dn, description):
        ou_attributes = {
            'objectClass': ['organizationalUnit'],
            'description': description,
        }
        self.conn.add(dn, attributes=ou_attributes)


@unittest.skipUnless(settings.USE_AUTH_LDAP_BACKEND, 'LDAP is not configured')
class LDAPUserTestCase(UserTestMixin, LDAPTestMixin, APITestCase):
    def setUp(self):
        # Login as admin to run admin-specific test cases
        self.create_user_and_login(is_staff=True, is_superuser=True)
        # Connect LDAP Server
        self.connect_ldap_server()
        # Create User, Group OU
        self.create_ldap_ou(settings.LDAP_USER_BASE, 'Users Organizational Unit')
        self.create_ldap_ou(settings.LDAP_GROUP_BASE, 'Groups Organizational Unit')
        # Create LDAP user via API
        self.create_ldap_user_via_api(is_staff=True, is_superuser=True)

    # Release resources and unbind LDAP connection after each test
    def tearDown(self):
        self.conn.unbind()

    def test_add_user_via_api(self):
        user_dn = settings.AUTH_LDAP_USER_DN_TEMPLATE % {'user': self.ldap_username}

        self.conn.search(search_base=user_dn, search_filter=f'(uid={self.ldap_username})')
        search_results = self.conn.entries
        self.assertEqual(len(search_results), 1, "User not found in LDAP server after creation")

    def test_delete_user_via_api(self):
        user_dn = settings.AUTH_LDAP_USER_DN_TEMPLATE % {'user': self.ldap_username}

        response = self.client.delete(
            reverse('api:iam:user-detail', args=(self.ldap_user.id,))
        )
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

        self.conn.search(search_base=user_dn, search_filter=f'(uid={self.ldap_username})')
        search_results = self.conn.entries
        self.assertEqual(len(search_results), 0, 'User still exists in LDAP server after deletion')

    def test_login_ldap_user(self):
        self.client.logout()

        self.login(self.ldap_username, self.ldap_password)
        response = self.client.get(reverse('api:auth:is-authenticated'))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['authenticated'])

    def test_change_information_by_ldap_user(self):
        user_dn = settings.AUTH_LDAP_USER_DN_TEMPLATE % {'user': self.ldap_username}

        self.client.logout()

        self.login(self.ldap_username, self.ldap_password)
        response = self.client.patch(
            reverse('api:iam:user-detail', args=(self.ldap_user.id,)), {
                'first_name': 'First',
                'last_name': 'Last',
                'email': 'alice@bob.com',
                'shell': '/test/test',
            })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        self.conn.search(
            search_base=user_dn,
            search_filter=f'(uid={self.ldap_username})',
            attributes=['givenName', 'sn', 'cn', 'mail', 'loginShell']
        )
        search_results = self.conn.entries
        self.assertEqual(len(search_results), 1, 'User not found in LDAP server')

        self.assertEqual(search_results[0]['givenName'].value, 'First', 'First name did not update correctly')
        self.assertEqual(search_results[0]['sn'].value, 'Last', 'Last name did not update correctly')
        self.assertEqual(search_results[0]['cn'].value, 'First Last', 'Full name did not update correctly')
        self.assertEqual(search_results[0]['mail'].value, 'alice@bob.com', 'Email did not update correctly')
        self.assertEqual(search_results[0]['loginshell'].value, '/test/test', 'LoginShell did not update correctly')

    def test_change_information_by_superuser(self):
        user_dn = settings.AUTH_LDAP_USER_DN_TEMPLATE % {'user': self.ldap_username}

        response = self.client.patch(
            reverse('api:iam:user-detail', args=(self.ldap_user.id,)), {
                'first_name': 'First',
                'last_name': 'Last',
                'email': 'alice@bob.com',
                'shell': '/test/test',
            })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        self.conn.search(
            search_base=user_dn,
            search_filter=f'(uid={self.ldap_username})',
            attributes=['givenName', 'sn', 'cn', 'mail', 'loginShell']
        )
        search_results = self.conn.entries
        self.assertEqual(len(search_results), 1, "User not found in LDAP server")

        self.assertEqual(search_results[0]['givenName'].value, 'First', 'First name did not update correctly')
        self.assertEqual(search_results[0]['sn'].value, 'Last', 'Last name did not update correctly')
        self.assertEqual(search_results[0]['cn'].value, 'First Last', 'Full name did not update correctly')
        self.assertEqual(search_results[0]['mail'].value, 'alice@bob.com', 'Email did not update correctly')
        self.assertEqual(search_results[0]['loginshell'].value, '/test/test', 'LoginShell did not update correctly')

    def test_change_password_by_ldap_user(self):
        self.client.logout()
        self.login(self.ldap_username, self.ldap_password)

        new_password = get_random_string(32)
        response = self.client.post(reverse('api:auth:change-password'), {
            'password': self.ldap_password,
            'new_password': new_password,
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        # current session should be alive.
        response = self.client.get(reverse('api:auth:is-authenticated'))
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['authenticated'])

        # test new password
        self.client.logout()
        self.assertFalse(self.client.login(username=self.ldap_username, password=self.ldap_password))
        self.assertTrue(self.client.login(username=self.ldap_username, password=new_password))


@unittest.skipUnless(settings.USE_AUTH_LDAP_BACKEND, 'LDAP is not configured')
class LDAPGroupTestCase(GroupTestMixin, LDAPTestMixin, APITestCase):
    def setUp(self):
        # Login as admin to run admin-specific test cases
        self.create_user_and_login(is_staff=True, is_superuser=True)
        # Connect LDAP Server
        self.connect_ldap_server()
        # Create User, Group OU
        self.create_ldap_ou(settings.LDAP_USER_BASE, 'Users Organizational Unit')
        self.create_ldap_ou(settings.LDAP_GROUP_BASE, 'Groups Organizational Unit')
        # Create LDAP Group vi API
        self.create_ldap_group_via_api()

    # Release resources and unbind LDAP connection after each test
    def tearDown(self):
        self.conn.unbind()

    def test_add_group_via_api(self):
        group_dn = settings.AUTH_LDAP_GROUP_DN_TEMPLATE % {'group': self.groupname}

        self.conn.search(search_base=group_dn, search_filter=f'(cn={self.groupname})')
        search_results = self.conn.entries
        self.assertEqual(len(search_results), 1, 'Group not found in LDAP server after creation')

    def test_delete_group_via_api(self):
        group_dn = settings.AUTH_LDAP_GROUP_DN_TEMPLATE % {'group': self.groupname}

        response = self.client.delete(
            reverse('api:iam:group-detail', args=(self.group.id,))
        )
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

        self.conn.search(search_base=group_dn, search_filter=f'(cn={self.groupname})')
        search_results = self.conn.entries
        self.assertEqual(len(search_results), 0, 'Group still exists in LDAP server after deletion')


@unittest.skipUnless(settings.USE_AUTH_LDAP_BACKEND, 'LDAP is not configured')
class GroupMemberTestCase(MembershipTestMixin, LDAPTestMixin, APITestCase):
    def setUp(self):
        # Connect LDAP Server
        self.connect_ldap_server()
        # Create User, Group OU
        self.create_ldap_ou(settings.LDAP_USER_BASE, 'Users Organizational Unit')
        self.create_ldap_ou(settings.LDAP_GROUP_BASE, 'Groups Organizational Unit')

        self.create_user_and_login(is_staff=True)
        response = self.create_ldap_group_via_api()
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('id' in response.data)
        self.group_id = response.data['id']

    # Release resources and unbind LDAP connection after each test
    def tearDown(self):
        self.conn.unbind()

    def test_add_member(self):
        # Setup: Create user and add to group
        group_dn = settings.AUTH_LDAP_GROUP_DN_TEMPLATE % {'group': self.groupname}
        created_uids = [
            self.create_ldap_user_and_add_member_via_api(role)['username']
            for role in ['owner', 'manager', 'member']
        ]

        # Create an additional user via API
        response = self.create_ldap_user_via_api()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        user = response.data

        # Add the new user to the group
        response = self.client.post(
            reverse('api:iam:membership-list'),
            {'group': self.group_id, 'user': user['id']}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['role'], 'member')

        # Verify the number of group members via API
        response = self.client.get(f"{reverse('api:iam:membership-list')}?group={self.group_id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)

        # Check LDAP to ensure the group contains the correct members
        self.conn.search(search_base=group_dn, search_filter=f'(cn={self.groupname})', attributes=['member'])
        ldap_group = self.conn.entries[0]
        ldap_uids = {member.split(',')[0].split('=')[1] for member in ldap_group['member']}
        self.assertTrue(set(created_uids).issubset(ldap_uids), 'Members in the group did not match')

    def test_delete_member(self):
        # Setup: Create user and add to group
        user = self.create_ldap_user_and_add_member_via_api('member')
        created_uid = user['username']
        membership_id = self.get_membership_id(user['id'])
        group_dn = settings.AUTH_LDAP_GROUP_DN_TEMPLATE % {'group': self.groupname}

        # Delete the membership via API
        response = self.client.delete(reverse('api:iam:membership-detail', args=(membership_id,)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check if member is removed from the group in LDAP
        self.conn.search(search_base=group_dn, search_filter=f'(cn={self.groupname})', attributes=['member'])
        ldap_group = self.conn.entries[0]
        ldap_uids = set(member.split(',')[0].split('=')[1] for member in ldap_group['member'])
        self.assertNotIn(created_uid, ldap_uids, 'Members in the group did not match')

    def test_delete_user_from_group(self):
        # Setup: Create user and add to group
        user = self.create_ldap_user_and_add_member_via_api('member')
        user_dn = settings.AUTH_LDAP_USER_DN_TEMPLATE % {'user': user['username']}
        group_dn = settings.AUTH_LDAP_GROUP_DN_TEMPLATE % {'group': self.groupname}
        created_uid = user['username']

        # Delete the user via API
        response = self.client.delete(reverse('api:iam:user-detail', args=(user['id'],)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check if user is deleted in LDAP
        self.conn.search(search_base=user_dn, search_filter=f"(uid={created_uid})")
        self.assertEqual(len(self.conn.entries), 0, 'User still exists in LDAP server after deletion')

        # Check if user is removed from the member of group in LDAP
        self.conn.search(search_base=group_dn, search_filter=f'(cn={self.groupname})', attributes=['member'])
        ldap_group = self.conn.entries[0]
        ldap_uids = set(member.split(',')[0].split('=')[1] for member in ldap_group['member'])
        self.assertNotIn(created_uid, ldap_uids, 'Members in the group did not match')
