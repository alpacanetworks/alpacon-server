from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.utils import timezone

from rest_framework.test import APITestCase
from rest_framework import status

from iam.models import Group, Membership
from iam.test_user import get_random_username


User = get_user_model()


class MembershipModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=get_random_username(),
            password=get_random_string(32),
        )
        self.group = Group.objects.create(
            name=get_random_username()
        )
        Membership.objects.create(
            group=self.group,
            user=self.user,
            role='owner',
        )

    def test_create(self):
        self.assertEquals(Membership.objects.filter(
            group__pk=self.group.pk,
            user__pk=self.user.pk,
        ).count(), 1)

    def test_delete_user(self):
        self.user.delete()
        self.assertEquals(Membership.objects.filter(
            group__pk=self.group.pk,
            user__pk=self.user.pk,
        ).count(), 0)

    def test_delete_group(self):
        self.group.delete()
        self.assertEquals(Membership.objects.filter(
            group__pk=self.group.pk,
            user__pk=self.user.pk,
        ).count(), 0)

    def test_disable_user(self):
        self.user.is_active = False
        self.user.deleted_at = timezone.now()
        self.user.save()
        self.assertEquals(Membership.objects.filter(
            group__pk=self.group.pk,
            user__pk=self.user.pk,
        ).count(), 0)


class MembershipTestMixin:
    def create_user(self, **kwargs):
        return User.objects.create_user(
            username=get_random_username(),
            password=self.password,
            **kwargs
        )

    def create_user_and_login(self, **kwargs):
        self.password = get_random_string(32)
        self.user = self.create_user(**kwargs)
        self.client.login(username=self.user.username, password=self.password)

    def create_user_via_api(self, **kwargs):
        username = get_random_username()
        return self.client.post(reverse('api:iam:user-list'), {
            'username': username,
            'password': get_random_string(32),
            'first_name': get_random_string(8),
            'last_name': get_random_string(8),
            'email': username + '@alpacon.io',
            **kwargs
        })

    def create_group(self, **kwargs):
        return Group.objects.create(
            name=get_random_username(),
            display_name=get_random_string(32),
            **kwargs
        )

    def create_group_via_api(self, **kwargs):
        return self.client.post(reverse('api:iam:group-list'), {
            'name': get_random_username(),
            'display_name': get_random_string(32),
            'tags': get_random_string(32),
            'description': get_random_string(128),
            **kwargs
        })

    def create_user_and_add_member(self, role):
        user = self.create_user()
        Membership.objects.create(
            group=Group.objects.get(pk=self.group_id),
            user=user,
            role=role,
        )
        return user

    def create_user_and_add_member_via_api(self, role):
        response = self.create_user_via_api()
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


class GroupOwnerTestCase(MembershipTestMixin, APITestCase):
    def setUp(self):
        self.create_user_and_login(is_staff=True)
        response = self.create_group_via_api()
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('id' in response.data)
        self.group_id = response.data['id']

    def test_get_membership(self):
        response = self.client.get(reverse('api:iam:membership-list') + '?group=%s' % self.group_id)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertEquals(str(response.data[0]['group']), str(self.group_id))
        self.assertEquals(str(response.data[0]['user']), str(self.user.id))
        self.assertEquals(response.data[0]['role'], 'owner')

    def test_add_members(self):
        self.create_user_and_add_member_via_api('owner')
        self.create_user_and_add_member_via_api('manager')
        self.create_user_and_add_member_via_api('member')

        response = self.create_user_via_api()
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('id' in response.data)
        user = response.data
        response = self.client.post(reverse('api:iam:membership-list'), {
            'group': self.group_id,
            'user': user['id'],
        })
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertEquals(response.data['role'], 'member')

        response = self.client.get(reverse('api:iam:membership-list') + '?group=%s' % self.group_id)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 5)

    def test_add_duplicated_member(self):
        user = self.create_user_and_add_member_via_api('member')
        response = self.client.post(reverse('api:iam:membership-list'), {
            'group': self.group_id,
            'user': user['id'],
            'role': 'manager',
        })
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_member(self):
        user = self.create_user_and_add_member_via_api('member')
        membership_id = self.get_membership_id(user['id'])

        response = self.client.delete(reverse('api:iam:membership-detail', args=(membership_id,)))
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_manager(self):
        user = self.create_user_and_add_member_via_api('manager')
        membership_id = self.get_membership_id(user['id'])

        response = self.client.delete(reverse('api:iam:membership-detail', args=(membership_id,)))
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_owner(self):
        user = self.create_user_and_add_member_via_api('owner')
        membership_id = self.get_membership_id(user['id'])

        response = self.client.delete(reverse('api:iam:membership-detail', args=(membership_id,)))
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_self_without_owner(self):
        membership_id = self.get_membership_id(self.user.id)
        response = self.client.delete(reverse('api:iam:membership-detail', args=(membership_id,)))
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_self(self):
        self.create_user_and_add_member_via_api('owner')
        membership_id = self.get_membership_id(self.user.id)

        response = self.client.delete(reverse('api:iam:membership-detail', args=(membership_id,)))
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_add_deleted_member_again(self):
        user = self.create_user_and_add_member_via_api('member')
        membership_id = self.get_membership_id(user['id'])

        response = self.client.delete(reverse('api:iam:membership-detail', args=(membership_id,)))
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.post(reverse('api:iam:membership-list'), {
            'group': self.group_id,
            'user': user['id'],
            'role': 'member',
        })
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_update_membership(self):
        user1 = self.create_user_and_add_member_via_api('member')
        user2 = self.create_user_and_add_member_via_api('member')
        membership_id = self.get_membership_id(user1['id'])

        # member -> manager
        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'role': 'manager',
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data['role'], 'manager')

        # manager -> onwer
        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'role': 'owner',
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data['role'], 'owner')

        # owner -> member
        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'role': 'member',
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data['role'], 'member')

        # user field will not change
        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'user': user2['id'],
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(str(response.data['user']), user1['id'])

    def test_update_membership_self_without_owner(self):
        membership_id = self.get_membership_id(self.user.id)
        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'role': 'member',
        })
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_membership_self(self):
        self.create_user_and_add_member_via_api('owner')
        membership_id = self.get_membership_id(self.user.id)
        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'role': 'member',
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_delete_owner_user(self):
        self.create_user_and_add_member_via_api('owner')

        response = self.client.delete(
            reverse('api:iam:user-detail', args=('-',))
        )
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_only_owner_user(self):
        response = self.client.delete(
            reverse('api:iam:user-detail', args=('-',))
        )
        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)


class GroupManagerTestCase(MembershipTestMixin, APITestCase):
    def setUp(self):
        self.create_user_and_login(is_staff=True)
        response = self.create_group_via_api()
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('id' in response.data)
        self.group_id = response.data['id']

        self.manager = self.create_user(is_staff=True)
        response = self.client.post(reverse('api:iam:membership-list'), {
            'group': self.group_id,
            'user': self.manager.id,
            'role': 'manager',
        })
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.client.logout()
        self.client.login(username=self.manager.username, password=self.password)

    def test_get_membership(self):
        response = self.client.get(reverse('api:iam:membership-list') + '?group=%(group)s&user=%(user)s' % {
            'group': self.group_id,
            'user': self.manager.id,
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertEquals(str(response.data[0]['group']), str(self.group_id))
        self.assertEquals(str(response.data[0]['user']), str(self.manager.id))
        self.assertEquals(response.data[0]['role'], 'manager')

    def test_add_member(self):
        response = self.create_user_via_api()
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('id' in response.data)
        user = response.data
        response = self.client.post(reverse('api:iam:membership-list'), {
            'group': self.group_id,
            'user': user['id'],
            'role': 'member',
        })
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertEquals(response.data['role'], 'member')

    def test_add_manager(self):
        response = self.create_user_via_api()
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('id' in response.data)
        user = response.data
        response = self.client.post(reverse('api:iam:membership-list'), {
            'group': self.group_id,
            'user': user['id'],
            'role': 'manager',
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_owner(self):
        response = self.create_user_via_api()
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('id' in response.data)
        user = response.data
        response = self.client.post(reverse('api:iam:membership-list'), {
            'group': self.group_id,
            'user': user['id'],
            'role': 'owner',
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_member(self):
        user = self.create_user_and_add_member_via_api('member')
        membership_id = self.get_membership_id(user['id'])

        response = self.client.delete(reverse('api:iam:membership-detail', args=(membership_id,)))
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_manager(self):
        user = self.create_user_and_add_member_via_api('member')
        membership_id = self.get_membership_id(user['id'])
        Membership.objects.filter(pk=membership_id).update(role='manager')

        response = self.client.delete(reverse('api:iam:membership-detail', args=(membership_id,)))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_owner(self):
        user = self.create_user_and_add_member_via_api('member')
        membership_id = self.get_membership_id(user['id'])
        Membership.objects.filter(pk=membership_id).update(role='owner')

        response = self.client.delete(reverse('api:iam:membership-detail', args=(membership_id,)))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_self(self):
        membership_id = self.get_membership_id(self.manager.id)

        response = self.client.delete(reverse('api:iam:membership-detail', args=(membership_id,)))
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_update_membership_from_member(self):
        user = self.create_user_and_add_member_via_api('member')
        membership_id = self.get_membership_id(user['id'])

        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'role': 'manager',
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'role': 'owner',
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_membership_from_manager(self):
        user = self.create_user_and_add_member_via_api('member')
        membership_id = self.get_membership_id(user['id'])
        Membership.objects.filter(pk=membership_id).update(role='manager')

        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'role': 'member',
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'role': 'owner',
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_membership_from_owner(self):
        user = self.create_user_and_add_member_via_api('member')
        membership_id = self.get_membership_id(user['id'])
        Membership.objects.filter(pk=membership_id).update(role='owner')

        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'role': 'member',
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'role': 'manager',
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)


class GroupMemberTestCase(MembershipTestMixin, APITestCase):
    def setUp(self):
        self.create_user_and_login(is_staff=True)
        response = self.create_group_via_api()
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('id' in response.data)
        self.group_id = response.data['id']

        self.member = self.create_user(is_staff=True)
        response = self.client.post(reverse('api:iam:membership-list'), {
            'group': self.group_id,
            'user': self.member.id,
            'role': 'member',
        })
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.client.logout()
        self.client.login(username=self.member.username, password=self.password)

    def test_get_membership(self):
        response = self.client.get(reverse('api:iam:membership-list') + '?group=%(group)s&user=%(user)s' % {
            'group': self.group_id,
            'user': self.member.id,
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertEquals(str(response.data[0]['group']), str(self.group_id))
        self.assertEquals(str(response.data[0]['user']), str(self.member.id))
        self.assertEquals(response.data[0]['role'], 'member')

    def test_add_member(self):
        user = self.create_user()
        response = self.client.post(reverse('api:iam:membership-list'), {
            'group': self.group_id,
            'user': user.id,
            'role': 'member',
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_manager(self):
        user = self.create_user()
        response = self.client.post(reverse('api:iam:membership-list'), {
            'group': self.group_id,
            'user': user.id,
            'role': 'manager',
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_owner(self):
        user = self.create_user()
        response = self.client.post(reverse('api:iam:membership-list'), {
            'group': self.group_id,
            'user': user.id,
            'role': 'owner',
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_member(self):
        user = self.create_user_and_add_member('member')
        membership_id = self.get_membership_id(user.id)

        response = self.client.delete(reverse('api:iam:membership-detail', args=(membership_id,)))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_manager(self):
        user = self.create_user_and_add_member('manager')
        membership_id = self.get_membership_id(user.id)

        response = self.client.delete(reverse('api:iam:membership-detail', args=(membership_id,)))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_owner(self):
        user = self.create_user_and_add_member('owner')
        membership_id = self.get_membership_id(user.id)

        response = self.client.delete(reverse('api:iam:membership-detail', args=(membership_id,)))
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_self(self):
        membership_id = self.get_membership_id(self.member.id)

        response = self.client.delete(reverse('api:iam:membership-detail', args=(membership_id,)))
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_update_membership_from_member(self):
        user = self.create_user_and_add_member('member')
        membership_id = self.get_membership_id(user.id)

        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'role': 'manager',
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'role': 'owner',
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_membership_from_manager(self):
        user = self.create_user_and_add_member('manager')
        membership_id = self.get_membership_id(user.id)

        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'role': 'member',
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'role': 'owner',
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_membership_from_owner(self):
        user = self.create_user_and_add_member('owner')
        membership_id = self.get_membership_id(user.id)

        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'role': 'member',
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.patch(reverse('api:iam:membership-detail', args=(membership_id,)), {
            'role': 'manager',
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)
