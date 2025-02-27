"""
URL configuration for unicef project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path, re_path
from rest_framework import routers

from .datamerge import views

router = routers.DefaultRouter()
router.register(r"encuestas", views.EncuestaViewSet)
router.register(r"colegios", views.ColegioViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(router.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("update_csv_completitud_by_comunidad/", views.update_csv_completitud_by_comunidad, name="update_csv_completitud_by_comunidad"),
    path("update_csv_previstas_by_comunidad/", views.update_csv_previstas_by_comunidad, name="update_csv_previstas_by_comunidad"),
]
