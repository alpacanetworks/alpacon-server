from rest_framework import routers

from events.api.views import *


app_name = 'events'

router = routers.DefaultRouter()
router.register('events', EventViewSet)
router.register('commands', CommandViewSet)

urlpatterns = router.urls
