# Generated by Django 4.1.1 on 2022-11-28 06:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('servers', '0003_server_load'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='server',
            options={'verbose_name': 'server', 'verbose_name_plural': 'servers'},
        ),
    ]
