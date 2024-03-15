from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError

from rest_framework import serializers

class WebshValidationSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        server = attrs.get('server', None)
        user = self.context['request'].user

        # Set default for username/groupname to handle None values, as their specific validate methods won't be called.
        attrs['username'] = attrs.get('username', user.username) or user.username
        attrs['groupname'] = attrs.get('groupname', '') or ''

        if not server:
            return attrs

        if not attrs['server'].commissioned:
            raise ValidationError(
                _('Requested server is not commissioned yet. Please finish the installation steps first.')
            )
        if not attrs['server'].is_connected:
            raise ValidationError(
                _("Requested server is not connected. Please check the server status first.")
            )

        if attrs['groupname'] == '':
            if attrs['server'].is_systemuser(attrs['username']):
                attrs['groupname'] = attrs['username']
            else:
                attrs['groupname'] = 'alpacon'

        if not attrs['server'].is_systemuser(attrs['username']):
            if attrs['username'] != user.username:  # No access with other IAM accounts
                raise ValidationError(
                    _('Username or groupname is not registered or you do not have permission.')
                )

        if not attrs['server'].has_access(
                user=user,
                username=attrs['username'],
                groupname=attrs['groupname'],
        ):
            raise ValidationError(
                _('Username or groupname is not registered or you do not have permission.')
            )

        return attrs