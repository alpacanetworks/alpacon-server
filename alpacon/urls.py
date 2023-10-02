from django.urls import path, include
from django.contrib import admin


admin.site.site_header = 'Alpacon'
admin.site.site_title = 'Alpacon'
admin.site.index_title = 'Administration'


urlpatterns = [
    path('api/', include('api.urls')),
    path('admin/', admin.site.urls),
]
