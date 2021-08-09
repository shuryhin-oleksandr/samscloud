from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import (UserCreateAPIView, VerifyMobileOTPAPIView, UserLoginAPIView,
                    ResendMobileNumberOTPAPIView, UserReportCreateAPIView, UpdateReportDetails,
                    ForgotPasswordAPIView,
                    ForgotPasswordVerifyAPIView, ResetPasswordAPIView,
                    UserReportLocationListAPIView,
                    SendMobileNumberOTPAPIView,
                    StatusCreateAPIView, LastUpdatedAPIView, UserTestingCreateAPIView,
                    UpdateUserTestingDetails,
                    UserTestingDeleteView, UserReportStatusUpdateAPIView, ScreeningUserViewSet,
                    ScreeningViewSet, ScreeningAnswerViewSet, ScreeningQuestionViewSet,
                    ScreeningQuestionOptionViewSet)

urlpatterns = [
    path('', UserCreateAPIView.as_view(), name='user_list_create'),
    path('verify-otp/', VerifyMobileOTPAPIView.as_view(), name='verify-otp'),
    path('login/', UserLoginAPIView.as_view(), name='login'),
    path('resent-otp/', ResendMobileNumberOTPAPIView.as_view(), name='resent-otp'),
    path('user-report/', UserReportCreateAPIView.as_view(), name='user_report_create'),
    path("user-report/<int:report_id>/update/", UpdateReportDetails.as_view(), name="list_update_report"),
    path("user-report-status/", UserReportStatusUpdateAPIView.as_view(), name="user_report_status"),
    path('forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot-password'),
    path('forgot-password-verify-otp/', ForgotPasswordVerifyAPIView.as_view(),name='forgot-password-verify-otp'),
    path('forgot-password-update/', ResetPasswordAPIView.as_view(), name='forgot-password-update'),
    path('user-report-locations/<str:country>/', UserReportLocationListAPIView.as_view(),name='user_reportlocation_view'),
    path('sent-otp/', SendMobileNumberOTPAPIView.as_view(), name='sent-otp'),
    path('list-status/', StatusCreateAPIView.as_view(), name='status_list_view'),
    path('last-updated/', LastUpdatedAPIView.as_view(), name='last_updated_view'),
    path('user-testing/', UserTestingCreateAPIView.as_view(), name='testing_list_view'),
    path("user-testing/<int:testing_id>/update/", UpdateUserTestingDetails.as_view(), name="update_user_testing"),
    path("user-testing/<int:testing_id>/delete/", UserTestingDeleteView.as_view(), name="delete_user_testing"),
]

router = SimpleRouter()

router.register('screenings', ScreeningViewSet, 'screening')
router.register('screening-users', ScreeningUserViewSet, 'screening-user')
router.register('screening-answers', ScreeningAnswerViewSet, 'screening-user')
router.register('screening-questions', ScreeningQuestionViewSet, 'screening-user')
router.register('screening-question-options', ScreeningQuestionOptionViewSet, 'screening-user')

urlpatterns += router.urls
