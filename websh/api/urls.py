from rest_framework import routers

from websh.api.views import SessionViewSet, UploadedFileViewSet, DownloadedFileViewSet


app_name = 'websh'

router = routers.DefaultRouter()
router.register('sessions', SessionViewSet)
router.register('uploads', UploadedFileViewSet)
router.register('downloads', DownloadedFileViewSet)

urlpatterns = router.urls
