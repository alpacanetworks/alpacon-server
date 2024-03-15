from rest_framework import routers

from proc.api.views import *


app_name = 'proc'

router = routers.DefaultRouter()
router.register('info', SystemInfoViewSet)
router.register('os', OsVersionViewSet)
router.register('time', SystemTimeViewSet)
router.register('users', SystemUserViewSet)
router.register('groups', SystemGroupViewSet)
router.register('interfaces', InterfaceViewSet)
router.register('packages', SystemPackageViewSet)
router.register('pypackages', PythonPackageViewSet)

urlpatterns = router.urls
