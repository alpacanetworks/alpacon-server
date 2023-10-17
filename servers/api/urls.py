from rest_framework import routers
from rest_framework.urls import path

from servers.api.views import ServerViewSet, NoteViewSet, RetrieveInstallerView


app_name = 'servers'

router = routers.DefaultRouter()
router.register('servers', ServerViewSet)
router.register('notes', NoteViewSet)

urlpatterns = router.urls + [
    path('installers/<uuid:pk>/', RetrieveInstallerView.as_view(), name='installer-detail'),
]
