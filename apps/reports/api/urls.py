from django.urls import path
from .views import (
    ReportTypeListAPIView,
    ReportCreateAPIView,
    ReportUpdateAPIView,
    ReportRetrieveAPIView,
    ReportDeleteAPIView,
    ReportFileUploadAPIView,
    GetUserReportsAPIView
)

urlpatterns = [
    path('report-types/', ReportTypeListAPIView.as_view(), name='report-types'),
    path('report-create/', ReportCreateAPIView.as_view(), name='report-create'),
    path('<int:pk>/report-update/', ReportUpdateAPIView.as_view(), name='report-update'),
    path('<int:pk>/report-retrieve/', ReportRetrieveAPIView.as_view(), name='report-retrieve'),
    path('<int:pk>/report-delete/', ReportDeleteAPIView.as_view(), name='report-delete'),
    path('report-file-upload/', ReportFileUploadAPIView.as_view(), name='report-file-upload'),
    path('get-user-reports/', GetUserReportsAPIView.as_view(), name='get-user-reports'),
]
