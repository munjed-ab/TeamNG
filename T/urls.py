
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls import handler404

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("project_manager.urls")),
    path("apis/", include("project_manager.api.urls")),
]
if settings.DEBUG:
    #NOT in production
    from django.conf.urls.static import static
    urlpatterns += static(settings.STATIC_URL, document_root = settings.STATIC_ROOT)

handler404 = 'project_manager.views.handler404'