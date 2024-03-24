from rest_framework import permissions

from api.apitoken.models import APIToken

class CommandACLObjectPermission(permissions.BasePermission):
    """
    Prohibits creating, modifying, or accessing other Command ACLs when accessed with an APIToken.
    """

    def has_permission(self, request, view):
        auth = request.auth
        if isinstance(auth, APIToken) and auth.source == 'api':
            return False

        return True
