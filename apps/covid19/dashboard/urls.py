from django.urls import path

from apps.covid19.dashboard.views import DashboardResultsView

urlpatterns = [
    path('results/<int:organisation_id>/',
         DashboardResultsView.as_view(),
         name='location_dashboard')
]
