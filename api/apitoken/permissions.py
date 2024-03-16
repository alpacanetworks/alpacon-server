from rest_framework import permissions

from api.apitoken.models import APIToken

class APITokenObjectPermission(permissions.BasePermission):
    """
    When accessing with a APIToken, creating, modifying, or accessing other APITokens is prohibited.
    """

    def has_permission(self, request, view):
        auth = request.auth
        if isinstance(auth, APIToken) and auth.source == 'api':
            return False

        return True
