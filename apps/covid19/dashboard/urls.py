from django.urls import path

from apps.covid19.dashboard.views import DashboardChartGraphView

urlpatterns = [
    path('chart_graph/<int:organisation_id>/', DashboardChartGraphView.as_view(),
         name='chart_graph')
]
