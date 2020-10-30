"""samscloud_api URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
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
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from rest_framework_swagger.views import get_swagger_view

schema_view = get_swagger_view(title='Samscloud API')

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include(('apps.accounts.api.urls', 'apps.accounts'), namespace='account-api')),
    path('api/organization/', include(('apps.organization.api.urls', 'apps.organization'), namespace='organization-api')),
    path('api/incidents/', include(('apps.incident.api.urls', 'apps.incident'), namespace='incident-api')),
    path('api/reports/', include(('apps.reports.api.urls', 'apps.reports'), namespace='report-api')),
    path('api-documentation/', schema_view),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh')
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
