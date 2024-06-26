# Generated by Django 4.0.6 on 2022-09-06 12:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('servers', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PtyChannel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel_name', models.CharField(editable=False, max_length=128, verbose_name='channel name')),
                ('remote_ip', models.GenericIPAddressField(verbose_name='remote IP address')),
                ('opened_at', models.DateTimeField(auto_now_add=True, verbose_name='opened at')),
                ('closed_at', models.DateTimeField(editable=False, null=True, verbose_name='closed_at')),
            ],
            options={
                'verbose_name': 'pty channel',
                'verbose_name_plural': 'pty channels',
            },
        ),
        migrations.CreateModel(
            name='UserChannel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel_name', models.CharField(editable=False, max_length=128, verbose_name='channel name')),
                ('remote_ip', models.GenericIPAddressField(verbose_name='remote IP address')),
                ('opened_at', models.DateTimeField(auto_now_add=True, verbose_name='opened at')),
                ('closed_at', models.DateTimeField(editable=False, null=True, verbose_name='closed_at')),
                ('user_agent', models.CharField(default='', editable=False, max_length=256, verbose_name='user agent')),
            ],
            options={
                'verbose_name': 'user channel',
                'verbose_name_plural': 'user channels',
            },
        ),
        migrations.CreateModel(
            name='Session',
            fields=[
                ('added_at', models.DateTimeField(auto_now_add=True, verbose_name='added at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('deleted_at', models.DateTimeField(editable=False, null=True, verbose_name='deleted at')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False, verbose_name='ID')),
                ('rows', models.PositiveSmallIntegerField(default=0, verbose_name='terminal rows')),
                ('cols', models.PositiveSmallIntegerField(default=0, verbose_name='terminal cols')),
                ('user_token', models.CharField(max_length=32, verbose_name='user token')),
                ('pty_token', models.CharField(max_length=32, verbose_name='pty token')),
                ('record', models.TextField(default='', verbose_name='record')),
                ('closed_at', models.DateTimeField(editable=False, null=True, verbose_name='closed_at')),
                ('server', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='servers.server', verbose_name='server')),
                ('user', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
            options={
                'verbose_name': 'session',
                'verbose_name_plural': 'sessions',
            },
        ),
    ]
