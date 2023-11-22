from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from rest_framework.test import APITestCase
from rest_framework import status

from iam.models import Group, Membership
from iam.test_user import get_random_username


User = get_user_model()


class GroupTestMixin:
    def create_user_and_login(self, **kwargs):
        self.password = get_random_string(32)
        self.user = User.objects.create_user(
            username=get_random_username(),
            password=self.password,
            **kwargs
        )
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


class UserTestCase(GroupTestMixin, APITestCase):
    def setUp(self):
        self.create_user_and_login()

    def test_create_by_user(self):
        response = self.create_group_via_api()
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_by_user(self):
        group = self.create_group()
        response = self.client.patch(
            reverse('api:iam:group-detail', args=(group.id,)), {
                'tags': get_random_string(32),
                'description': get_random_string(128),
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_by_user(self):
        group = self.create_group()
        response = self.client.delete(
            reverse('api:iam:group-detail', args=(group.id,))
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)


class StaffTestCase(GroupTestMixin, APITestCase):
    def setUp(self):
        self.create_user_and_login(is_staff=True)

    def test_create_by_staff(self):
        response = self.create_group_via_api()
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('id' in response.data)

        self.assertTrue(
            Membership.objects.filter(
                group__pk=response.data['id'],
                user__pk=self.user.id,
                role='owner',
            ).exists()
        )

    def test_update_by_owner(self):
        response = self.create_group_via_api()
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('id' in response.data)
        group_id = response.data['id']
        
        response = self.client.patch(
            reverse('api:iam:group-detail', args=(group_id,)), {
                'tags': get_random_string(32),
                'description': get_random_string(128),
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_update_by_manager(self):
        group = self.create_group()
        group.membership_set.create(
            user=self.user,
            role='manager',
        )
        response = self.client.patch(
            reverse('api:iam:group-detail', args=(group.id,)), {
                'tags': get_random_string(32),
                'description': get_random_string(128),
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_update_by_member(self):
        group = self.create_group()
        group.membership_set.create(
            user=self.user,
            role='member',
        )
        response = self.client.patch(
            reverse('api:iam:group-detail', args=(group.id,)), {
                'tags': get_random_string(32),
                'description': get_random_string(128),
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_by_nonmember(self):
        group = self.create_group()
        response = self.client.patch(
            reverse('api:iam:group-detail', args=(group.id,)), {
                'tags': get_random_string(32),
                'description': get_random_string(128),
        })
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_by_owner(self):
        response = self.create_group_via_api()
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('id' in response.data)
        group_id = response.data['id']
        
        response = self.client.delete(
            reverse('api:iam:group-detail', args=(group_id,))
        )
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_by_manager(self):
        group = self.create_group()
        group.membership_set.create(
            user=self.user,
            role='manager',
        )
        response = self.client.delete(
            reverse('api:iam:group-detail', args=(group.id,))
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_by_member(self):
        group = self.create_group()
        group.membership_set.create(
            user=self.user,
            role='member',
        )
        response = self.client.delete(
            reverse('api:iam:group-detail', args=(group.id,))
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_by_nonmember(self):
        group = self.create_group()
        response = self.client.delete(
            reverse('api:iam:group-detail', args=(group.id,))
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)


class SuperuserTestCase(GroupTestMixin, APITestCase):
    def setUp(self):
        self.create_user_and_login(is_staff=True, is_superuser=True)

    def test_create_by_superuser(self):
        response = self.create_group_via_api()
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_update_by_owner(self):
        response = self.create_group_via_api()
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('id' in response.data)
        group_id = response.data['id']
        
        response = self.client.patch(
            reverse('api:iam:group-detail', args=(group_id,)), {
                'tags': get_random_string(32),
                'description': get_random_string(128),
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_update_by_manager(self):
        group = self.create_group()
        group.membership_set.create(
            user=self.user,
            role='manager',
        )
        response = self.client.patch(
            reverse('api:iam:group-detail', args=(group.id,)), {
                'tags': get_random_string(32),
                'description': get_random_string(128),
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_update_by_member(self):
        group = self.create_group()
        group.membership_set.create(
            user=self.user,
            role='member',
        )
        response = self.client.patch(
            reverse('api:iam:group-detail', args=(group.id,)), {
                'tags': get_random_string(32),
                'description': get_random_string(128),
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_update_by_nonmember(self):
        group = self.create_group()
        response = self.client.patch(
            reverse('api:iam:group-detail', args=(group.id,)), {
                'tags': get_random_string(32),
                'description': get_random_string(128),
        })
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_delete_by_owner(self):
        response = self.create_group_via_api()
        self.assertEquals(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('id' in response.data)
        group_id = response.data['id']
        
        response = self.client.delete(
            reverse('api:iam:group-detail', args=(group_id,))
        )
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_by_manager(self):
        group = self.create_group()
        group.membership_set.create(
            user=self.user,
            role='manager',
        )
        response = self.client.delete(
            reverse('api:iam:group-detail', args=(group.id,))
        )
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_by_member(self):
        group = self.create_group()
        group.membership_set.create(
            user=self.user,
            role='member',
        )
        response = self.client.delete(
            reverse('api:iam:group-detail', args=(group.id,))
        )
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_by_nonmember(self):
        group = self.create_group()
        response = self.client.delete(
            reverse('api:iam:group-detail', args=(group.id,))
        )
        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)
