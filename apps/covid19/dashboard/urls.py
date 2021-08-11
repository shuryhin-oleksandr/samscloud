from django.urls import path

from apps.covid19.dashboard.views import DashboardChartGraphView
from apps.covid19.dashboard.views import DashboardResultsView

urlpatterns = [
    path('results/<int:organisation_id>/',
         DashboardResultsView.as_view(),
         name='location_dashboard'),
    path('chart_graph/<int:organisation_id>/',
         DashboardChartGraphView.as_view(),
         name='chart_graph')
]
