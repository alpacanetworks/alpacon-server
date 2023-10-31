from django.conf import settings

from rest_framework_simplejwt.tokens import RefreshToken

class JWTRefreshToken(RefreshToken):
    """
    Return a token object by putting the APIclient ID in the token claim, and create an access token using the refresh token.
    """

    @classmethod
    def for_client(cls, client_id):
        """
        Returns an authorization token for the given client that will be provided after authenticating the user's credentials.
        """

        token = cls()
        token[settings.SIMPLE_JWT['CLIENT_ID_CLAIM']] = str(client_id)
        return token