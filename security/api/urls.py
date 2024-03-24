from rest_framework import routers

from security.api.views import CommandACLViewSet

app_name ='security'

router = routers.DefaultRouter()
router.register('command_acl', CommandACLViewSet)

urlpatterns = router.urls
