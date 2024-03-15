import uuid

from django.core.serializers import deserialize
from django.db import migrations


def restore_channels(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('websh', '0011_remove_session_pty_websocket_url_userchannel_user'),
    ]

    operations = [
        migrations.RunPython(restore_channels),
    ]
