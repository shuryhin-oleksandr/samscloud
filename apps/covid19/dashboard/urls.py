from django.urls import path

from apps.covid19.dashboard.views import DashboardGraphView

urlpatterns = [
    path('graph/<int:organisation_id>/',
         DashboardGraphView.as_view(),
         name='dashboard_graph')
]
