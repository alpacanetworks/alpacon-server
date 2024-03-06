from rest_framework import routers

from iam.api.views import UserViewSet, GroupViewSet, MembershipViewSet


app_name = 'iam'

router = routers.DefaultRouter()
router.register('users', UserViewSet)
router.register('groups', GroupViewSet)
router.register('memberships', MembershipViewSet)

urlpatterns = router.urls
