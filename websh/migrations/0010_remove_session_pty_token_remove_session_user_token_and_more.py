# Generated by Django 4.2.3 on 2023-07-30 12:16

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('websh', '0009_remove_channel'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='session',
            name='pty_token',
        ),
        migrations.RemoveField(
            model_name='session',
            name='user_token',
        ),
        migrations.AddField(
            model_name='session',
            name='pty_websocket_url',
            field=models.URLField(default=''),
        ),
        migrations.CreateModel(
            name='UserChannel',
            fields=[
                ('added_at', models.DateTimeField(auto_now_add=True, verbose_name='added at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('deleted_at', models.DateTimeField(editable=False, null=True, verbose_name='deleted at')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=32, verbose_name='token')),
                ('channel_name', models.CharField(default='', editable=False, max_length=128, verbose_name='channel name')),
                ('remote_ip', models.GenericIPAddressField(editable=False, null=True, verbose_name='remote IP address')),
                ('opened_at', models.DateTimeField(editable=False, null=True, verbose_name='opened at')),
                ('closed_at', models.DateTimeField(editable=False, null=True, verbose_name='closed_at')),
                ('user_agent', models.CharField(default='', editable=False, max_length=256, verbose_name='user agent')),
                ('session', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='websh.session', verbose_name='session')),
            ],
            options={
                'verbose_name': 'user channel',
                'verbose_name_plural': 'user channels',
            },
        ),
        migrations.CreateModel(
            name='PtyChannel',
            fields=[
                ('added_at', models.DateTimeField(auto_now_add=True, verbose_name='added at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('deleted_at', models.DateTimeField(editable=False, null=True, verbose_name='deleted at')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=32, verbose_name='token')),
                ('channel_name', models.CharField(default='', editable=False, max_length=128, verbose_name='channel name')),
                ('remote_ip', models.GenericIPAddressField(editable=False, null=True, verbose_name='remote IP address')),
                ('opened_at', models.DateTimeField(editable=False, null=True, verbose_name='opened at')),
                ('closed_at', models.DateTimeField(editable=False, null=True, verbose_name='closed_at')),
                ('session', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='websh.session', verbose_name='session')),
            ],
            options={
                'verbose_name': 'pty channel',
                'verbose_name_plural': 'pty channels',
            },
        ),
    ]