from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from . import views


urlpatterns = [
    path('', views.home, name='homepage'),
    path('admin/', admin.site.urls),
    path('api/grade/', views.grade_papers, name='grade_papers'),
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

