from rest_framework import routers

from api.apitoken.views import *


app_name = 'apitoken'

router = routers.DefaultRouter()
router.register('sessions', LoginSessionViewSet, basename='loginsession')
router.register('tokens', APITokenViewSet)

urlpatterns = router.urls
