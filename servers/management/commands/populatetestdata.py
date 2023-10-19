from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from iam.models import Group
from servers.models import Server


User = get_user_model()

user_data = [
    {
        'username': 'admin',
        'password': 'admin',
        'first_name': 'Peter',
        'last_name': 'Parker',
        'email': 'admin@alpacanetworks.com',
        'phone': '+82-10-1234-5678',
        'tags': '#admin,#root,#ceo',
        'description': 'I am an administrator of this system. I can do everything that I want!!!',
        'is_staff': True,
        'is_superuser': True,
    }, {
        'username': 'scott',
        'password': 'scott',
        'first_name': 'Scott',
        'last_name': 'Dorris',
        'email': 'scott.dorris@alpacanetworks.com',
        'phone': '+1-209-239-6412',
        'tags': '#developer,#manager',
        'description': 'I am leading the development team. Please tell me if you have any inquiries about new features.',
        'is_staff': True,
    }, {
        'username': 'verna',
        'password': 'verna',
        'first_name': 'Verna',
        'last_name': 'Turley',
        'email': 'verna.turley@alpacanetworks.com',
        'phone': '+1-209-239-6413',
        'tags': '#developer',
        'description': 'I am a senior developer.',
    }, {
        'username': 'jimmy',
        'password': 'jimmy',
        'first_name': 'Jimmy',
        'last_name': 'Brown',
        'email': 'jimmy.brown@alpacanetworks.com',
        'phone': '+1-209-239-6414',
        'tags': '#developer',
    }, {
        'username': 'nancy',
        'password': 'nancy',
        'first_name': 'Nancy',
        'last_name': 'Linda',
        'email': 'nancy.linda@alpacanetworks.com',
        'phone': '+1-209-239-6415',
        'tags': '#developer',
    }, {
        'username': 'jack',
        'password': 'jack',
        'first_name': 'Jack',
        'last_name': 'Dorn',
        'email': 'jack.dorn@alpacanetworks.com',
        'tags': '#operator,#manager',
        'phone': '+49 07803 84 72 73',
        'description': 'I am leading the operating team. Please tell me if you see any incidents on the system.',
        'is_staff': True,
    }, {
        'username': 'donald',
        'password': 'donald',
        'first_name': 'Donald',
        'last_name': 'Duck',
        'email': 'donald.duck@alpacanetworks.com',
        'phone': '+33 01.85.70.37.04',
        'tags': '#operator',
    }, {
        'username': 'angelica',
        'password': 'angelica',
        'first_name': 'Angelica',
        'last_name': 'Ramos',
        'email': 'angelica@ramos.com',
        'tags': '#operator',
    }, {
        'username': 'brenden',
        'password': 'brenden',
        'first_name': 'Brenden',
        'last_name': 'Wagner',
        'email': 'brenden@wagner.com',
        'tags': '#staff',
        'description': 'I am chief operating officer of this company.',
        'is_staff': True,
    }, {
        'username': 'charde',
        'password': 'charde',
        'first_name': 'Charde',
        'last_name': 'Marshall',
        'email': 'charde@marshall.com',
        'tags': '#designer,#manager',
        'is_staff': True,
    }, {
        'username': 'doris',
        'password': 'doris',
        'first_name': 'Doris',
        'last_name': 'Wilder',
        'email': 'doris@wilder.com',
        'tags': '#designer',
    }, {
        'username': 'fiona',
        'password': 'fiona',
        'first_name': 'Fiona',
        'last_name': 'Green',
        'email': 'fiona@green.com',
        'tags': '#auditor',
    }, {
        'username': 'garrett',
        'password': 'garrett',
        'first_name': 'Garrett',
        'last_name': 'Winters',
        'email': 'garrett@winters.com',
        'tags': '#auditor',
    }, {
        'username': 'gavin',
        'password': 'gavin',
        'first_name': 'Gavin',
        'last_name': 'Cortez',
        'email': 'gavin@cortez.com',
    }, {
        'username': 'haley',
        'password': 'haley',
        'first_name': 'Haley',
        'last_name': 'Kennedy',
        'email': 'haley@kennedy.com',
    }, {
        'username': 'howard',
        'password': 'howard',
        'first_name': 'Howard',
        'last_name': 'Hatfield',
        'email': 'howard@hatfield.com',
    }
]

group_data = [
    {
        'name': 'developers',
        'display_name': 'Developers',
        'tags': '#developer',
        'description': 'Developers are allowed to access the servers when needed.',
        'members': [
            {'username': 'scott', 'role': 'owner'},
            {'username': 'verna', 'role': 'manager'},
            {'username': 'jimmy', 'role': 'member'},
            {'username': 'nancy', 'role': 'member'},
        ]
    }, {
        'name': 'operators',
        'display_name': 'Operators',
        'tags': '#operator',
        'description': 'Operators can access and manage servers. They also can login to the server as root.',
        'members': [
            {'username': 'jack', 'role': 'owner'},
            {'username': 'donald', 'role': 'member'},
            {'username': 'angelica', 'role': 'member'},
        ]
    }, {
        'name': 'auditors',
        'display_name': 'Auditors',
        'tags': '#auditor',
        'description': 'Auditors are not allowed to access the servers directly, but they can checkout the history of operations that others have done.',
        'members': [
            {'username': 'admin', 'role': 'owner'},
            {'username': 'fiona', 'role': 'member'},
            {'username': 'garrett', 'role': 'member'},
        ]
    }, {
        'name': 'designers',
        'display_name': 'Designers',
        'tags': '#designer',
        'members': [
            {'username': 'charde', 'role': 'owner'},
            {'username': 'doris', 'role': 'member'},
        ]
    }, {
        'name': 'managers',
        'display_name': 'Managers',
        'tags': '#manager',
        'members': [
            {'username': 'admin', 'role': 'owner'},
            {'username': 'brenden', 'role': 'manager'},
            {'username': 'scott', 'role': 'member'},
            {'username': 'jack', 'role': 'member'},
            {'username': 'charde', 'role': 'member'},
        ]
    }
]

server_data = [
    {
        'name': 'test',
        'id': '7a50ea6c-2138-4d3f-9633-e50694c847c4',
        'key': 'dkfvkzk',
    }, {
        'name': 'ubuntu-2204',
        'id': 'a7282bea-31d7-4b55-a43e-97e1240c90ab',
        'key': 'dkfvkzk',
    }, {
        'name': 'ubuntu-2004',
        'id': '617cfd44-a25e-4fc7-90e1-bfafe429c649',
        'key': 'dkfvkzk',
    }, {
        'name': 'ubuntu-1804',
        'id': '756d1a97-a4ec-4d76-a9a0-688f15416abf',
        'key': 'dkfvkzk',
    }, {
        'name': 'debian-11',
        'id': '71e4e4f9-3553-4554-8695-6425c34eb955',
        'key': 'dkfvkzk',
    }, {
        'name': 'debian-10',
        'id': 'd59bc536-2f33-43e0-8d78-bca3ecd91b8e',
        'key': 'dkfvkzk',
    }, {
        'name': 'redhat-9',
        'id': '97a27261-6029-48b3-89df-b31040a43722',
        'key': 'dkfvkzk',
    }, {
        'name': 'redhat-8',
        'id': 'ff79dd66-0cfa-4a29-902a-b023038b12e3',
        'key': 'dkfvkzk',
    }, {
        'name': 'centos-7',
        'id': '959ae5c7-84b0-4fba-8c1e-5b8a3d6dcadc',
        'key': 'dkfvkzk',
    }
]


class Command(BaseCommand):
    help = 'Populate basic dataset for tests'

    def handle(self, *args, **options):
        for data in user_data:
            if not User.objects.filter(username=data['username']).exists():
                User.objects.create_user(**data)

        Group.get_default()
        for data in group_data:
            if not Group.objects.filter(name=data['name']).exists():
                members = data.pop('members')
                group = Group.objects.create(**data)
                for membership in members:
                    group.membership_set.create(
                        user=User.objects.get(username=membership['username']),
                        role=membership['role'],
                    )

        admin_user = User.objects.get(username='admin')

        for data in server_data:
            if not Server.objects.filter(id=data['id']).exists():
                server = Server(**data, owner=admin_user)
                server.set_key(data['key'])
                server.save()

        print('We have populated dataset for your tests.')
        print('Please login using admin/admin.')
