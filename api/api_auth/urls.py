from django.urls import path, include
from django.conf import settings

from api.api_auth.views import *


app_name = 'auth'

urlpatterns = [
    path('', api_root, name='api-root'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('is_authenticated/', is_authenticated, name='is-authenticated'),
    path('csrf_token/', get_csrf_token, name='csrf-token'),
    path('change_password/', PasswordChangeView.as_view(), name='change-password'),
    path('reset_password/', include('api.password_reset.urls')),
]

if 'api.apitoken' in settings.INSTALLED_APPS:
    urlpatterns.append(
        path('', include('api.apitoken.urls'))
    )
