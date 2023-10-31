import logging

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView

from api.apiclient.serializers import JWTLoginSerializer
from api.apiclient.serializers import JWTRefreshSerializer


logger = logging.getLogger(__name__)


class JWTLoginView(TokenObtainPairView):
    """
    Takes the Client ID and key and returns the access token and refresh token.

    The two tokens are a pair of tokens that prove client authentication.
    """
    
    serializer_class = JWTLoginSerializer


class JWTRefreshView(TokenRefreshView):
    """
    Takes a refresh type JSON web token and returns an access type JSON web token if the refresh token is valid.
    """

    serializer_class = JWTRefreshSerializer
