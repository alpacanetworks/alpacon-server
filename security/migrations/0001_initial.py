# Generated by Django 4.2.9 on 2024-02-29 10:40

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('apitoken', '0003_apitoken_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='CommandACL',
            fields=[
                ('added_at', models.DateTimeField(auto_now_add=True, verbose_name='added at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('deleted_at', models.DateTimeField(editable=False, null=True, verbose_name='deleted at')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False, verbose_name='ID')),
                ('command', models.CharField(help_text='Specify the command this token is permitted to execute. Use exact commands or wildcard patterns for broader permissions.<br>Examples:<br>- docker * (allows all docker commands)<br>- docker compose up -d (allows specific docker-compose command)<br>- ls -la (allows listing directory contents in long format)<br>- cp * /destination (allows copying all files to a specified destination)', max_length=255, verbose_name='command')),
                ('token', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='apitoken.apitoken', verbose_name='token')),
            ],
            options={
                'verbose_name': 'Command ACL',
                'verbose_name_plural': 'Command ACLs',
            },
        ),
        migrations.AddConstraint(
            model_name='commandacl',
            constraint=models.UniqueConstraint(fields=('token', 'command'), name='unique_token_command'),
        ),
    ]
