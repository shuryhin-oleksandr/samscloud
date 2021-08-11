from django.urls import path

from apps.covid19.dashboard.views import DashboardGraphView
from apps.covid19.dashboard.views import DashboardChartGraphView
from apps.covid19.dashboard.views import DashboardResultsView

urlpatterns = [
    path('results/<int:organisation_id>/',
         DashboardResultsView.as_view(),
         name='location_dashboard'),
    path('graph/<int:organisation_id>/',
         DashboardGraphView.as_view(),
         name='dashboard_graph'),
    path('chart_graph/<int:organisation_id>/',
         DashboardChartGraphView.as_view(),
         name='chart_graph')
]
