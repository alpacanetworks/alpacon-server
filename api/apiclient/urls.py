from django.urls import include, path

from api.apiclient.views import JWTLoginView
from api.apiclient.views import JWTRefreshView


app_name = 'apiclient'


jwt_patterns = ([ 
    path('login/', JWTLoginView.as_view(), name='login'), 
    path('refresh/', JWTRefreshView.as_view(), name='refresh'),
], 'jwt')


urlpatterns = [
    path('jwt/', include(jwt_patterns)),
]
