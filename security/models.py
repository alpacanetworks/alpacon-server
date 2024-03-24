import re

from django.db import models
from django.db.models import UniqueConstraint
from django.utils.translation import gettext_lazy as _

from api.apitoken.models import APIToken
from utils.models import UUIDBaseModel


class CommandACL(UUIDBaseModel):
    """
    The CommandACL model defines command access for API tokens
    and enables setting specific commands that each API token can run.
    """

    token = models.ForeignKey(
        'apitoken.APIToken', on_delete=models.CASCADE,
        verbose_name=_('token')
    )
    command = models.CharField(
        _('command'),
        max_length=255,
        help_text=_(
            'Specify the command this token is permitted to execute. Use exact commands or wildcard patterns for broader permissions.<br>'
            'Examples:<br>'
            '- docker * (allows all docker commands)<br>'
            '- docker compose up -d (allows specific docker-compose command)<br>'
            '- ls -la (allows listing directory contents in long format)<br>'
            '- cp * /destination (allows copying all files to a specified destination)'
        )
    )

    class Meta:
        verbose_name = _('Command ACL')
        verbose_name_plural = _('Command ACLs')
        constraints = [
            UniqueConstraint(fields=['token', 'command'], name='unique_token_command')
        ]

    def __str__(self):
        return '(%s\'s command acl : `%s`)' % (str(self.token.name), self.command)

    @property
    def token_name(self):
        return str(self.token.name)

    @classmethod
    def is_allowed(cls, command: str, token: APIToken):
        for command_acl in cls.objects.filter(token__pk=token.pk).all():
            pattern = r'^' + re.escape(command_acl.command).replace("\\*", ".*") + r'$'
            if re.match(pattern, command):
                return True
        return False
