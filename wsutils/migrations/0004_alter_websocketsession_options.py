# Generated by Django 4.1.1 on 2022-10-16 06:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wsutils', '0003_auto_20221016_1145'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='websocketsession',
            options={'get_latest_by': 'updated_at', 'verbose_name': 'WebSocket session', 'verbose_name_plural': 'WebSocket sessions'},
        ),
    ]
