import datetime
import re
from random import randint

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import (ListCreateAPIView, CreateAPIView, RetrieveUpdateAPIView,
                                     DestroyAPIView, get_object_or_404)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_200_OK
from rest_framework.views import APIView

from apps.accounts.models import User, MobileOtp
from apps.covid19.covid_accounts.api.serializers import (UserCreateSerializer, MobileOTPSerializer,
                                                         UserLoginSerializer,
                                                         MobileNumberSerializer,
                                                         UserReportSerializer,
                                                         UserReportWriteSerializer,
                                                         ForgotPasswordSerializer,
                                                         MobileResetPasswordSerializer,
                                                         UserReportListSerializer,
                                                         MobilesNumberSerializer,
                                                         StatusSerializer,
                                                         LastUpdatedListSerializer,
                                                         UserTestingSerializer,
                                                         UserTestingUpdateSerializer,
                                                         UserReportStatusSerializer,
                                                         ScreeningUserDetailSerializer,
                                                         ScreeningDetailSerializer,
                                                         ScreeningSerializer,
                                                         ScreeningUserSerializer,
                                                         ScreeningQuestionDetailSerializer,
                                                         ScreeningQuestionSerializer,
                                                         ScreeningQuestionOptionSerializer,
                                                         ScreeningAnswerSerializer)
from apps.covid19.covid_accounts.models import (UserReport, Status, Disease, Lastupdated,
                                                UserTesting, ScreeningUser, Screening,
                                                ScreeningQuestion, ScreeningQuestionOption,
                                                ScreeningAnswer)
from apps.covid19.covid_accounts.utils import get_tokens_for_user, send_twilio_sms


class UserCreateAPIView(ListCreateAPIView):
    """
    User Register APIView
    """
    serializer_class = UserCreateSerializer
    queryset = User.objects.all()
    permission_classes = [AllowAny]


class VerifyMobileOTPAPIView(CreateAPIView):
    """
    API for mobile OTP verification
    """
    serializer_class = MobileOTPSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = MobileOTPSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            phone_number = data.get('phone_number')
            otp = data.get('otp')
            user = User.objects.filter(phone_number=phone_number).distinct()
            if user.exists() and user.count() == 1:
                user_obj = user.first()
            else:
                return Response('No user found for phone number %s' % phone_number, status=HTTP_400_BAD_REQUEST)
            if not MobileOtp.objects.filter(user=user_obj).exists():
                return Response("No otp user otp exists", status=HTTP_400_BAD_REQUEST)

            otp_obj = MobileOtp.objects.filter(user=user_obj).first()
            if otp == otp_obj.otp:
                user_obj.is_phone_number_verified = True
                user_obj.is_active = True
                user_obj.save()
                response_token = get_tokens_for_user(user_obj)
                token = response_token.get('access', None)
                refresh_token = response_token.get('refresh', None)
                user_id = user_obj.id
                if not (user_obj.is_active and user_obj.is_phone_number_verified):
                    verified_status = False
                else:
                    verified_status = True
                response_data = {
                    "msg": "Mobile number successfully verified",
                    "access_token": token,
                    "refresh_token": refresh_token,
                    "user_id": user_id,
                    "verified_status": verified_status,
                    "status": 200
                }
                return Response(response_data)
            else:
                return Response({"msg": "Invalid OTP"})
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class UserLoginAPIView(CreateAPIView):
    """
    User login APIView
    """
    permission_classes = [AllowAny]
    serializer_class = UserLoginSerializer

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = UserLoginSerializer(data=data, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            new_data = serializer.data
            return Response(new_data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ResendMobileNumberOTPAPIView(CreateAPIView):
    """
    API for sending mobile OTP
    """
    serializer_class = MobileNumberSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        user_obj = None
        data = request.data
        serializer = MobileNumberSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            mobile_number = data.get('mobile_number')
            user = User.objects.filter(phone_number=mobile_number).distinct()
            if user.exists() and user.count() == 1:
                user_obj = user.first()
            else:
                return Response('No user found for phone number %s' % mobile_number, status=HTTP_400_BAD_REQUEST)
            user_obj.phone_number = mobile_number
            user_obj.save()
            last_updated = Lastupdated(updated_time=timezone.now())
            last_updated.save()
            otp = self.generate_otp()
            if MobileOtp.objects.filter(user=user_obj).exists():
                otp_obj = MobileOtp.objects.filter(user=user_obj).first()
                otp_obj.otp = otp
                otp_obj.save()
            else:
                otp_obj = MobileOtp.objects.create(user=user_obj, otp=otp)
            message = "Your verification code is %s" % otp
            to = mobile_number
            send_twilio_sms.delay(message, to)
            return Response({"msg": "Message sent successfully", "status": 200})

    def generate_otp(self):
        otp = randint(1000, 9999)
        return otp


class UserReportCreateAPIView(ListCreateAPIView):
    """
    User Report Register APIView
    """
    serializer_class = UserReportWriteSerializer
    queryset = UserReport.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        return UserReport.objects.filter(user=user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = UserReportSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = UserReportSerializer(queryset, many=True)
        return Response(serializer.data)


class UpdateReportDetails(RetrieveUpdateAPIView):
    """
    View to retrieve patch update invoice details
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserReportWriteSerializer

    def get_object(self):
        report_id = self.kwargs["report_id"]
        return UserReport.objects.get(id=report_id)


class UserReportStatusUpdateAPIView(RetrieveUpdateAPIView):
    """
    View to retrieve patch update user report status
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserReportStatusSerializer

    def get_object(self):
        return get_object_or_404(UserReport, user=self.request.user)

    def put(self, request, *args, **kwargs):
        status = Status.objects.filter(id=self.request.data.get("status")).first()
        disease = Disease.objects.filter(id=self.request.data.get("disease", 1)).first()
        user = self.request.user
        if status.status == 'Infected':
            user.risk_level = True
        else:
            user.risk_level = False
        user.save()
        try:
            user_report = UserReport.objects.get(user=self.request.user)
            user_report.status = status
            if status.status == 'Infected':
                user_report.test_result = "Positive"
                user_report.is_tested = True
            else:
                user_report.test_result = "Negative"
                user_report.is_tested = False
            user_report.save()
            serializer = UserReportStatusSerializer(user_report)
            return Response(serializer.data)
        except ObjectDoesNotExist:
            if status.status == 'Infected':
                test_result = 'Positive'
                is_tested = True
            else:
                test_result = 'Negative'
                is_tested = False
            user_report = UserReport.objects.create(disease=disease, status=status, user=self.request.user,
                                                    test_result=test_result, is_tested=is_tested)
            serializer = UserReportStatusSerializer(user_report)
            return Response(serializer.data)


class ForgotPasswordAPIView(CreateAPIView):
    """
    API for sending mobile forgot password verification
    """
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer

    def generate_otp(self):
        otp = randint(1000, 9999)
        return otp

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = ForgotPasswordSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            phone_number = data.get("phone_number", None)
            user_obj = User.objects.get(phone_number=phone_number)
            otp = self.generate_otp()
            otp_obj, created = MobileOtp.objects.get_or_create(user=user_obj)
            otp_obj.otp = otp
            otp_obj.save()
            last_updated = Lastupdated(updated_time=timezone.now())
            last_updated.save()
            message = "Your verification code is %s" % otp
            to = user_obj.phone_number
            send_twilio_sms.delay(message, to)
            return Response("An OTP has been sent to %s" % (user_obj.phone_number), status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ForgotPasswordVerifyAPIView(CreateAPIView):
    """
    API for Mobile forgot password verification
    """
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = ForgotPasswordSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            phone_number = data.get("phone_number", None)
            otp = data.get("otp", None)
            user_obj = User.objects.get(phone_number=phone_number)
            otp_obj = MobileOtp.objects.get(user=user_obj)
            if otp_obj.otp == otp:
                return Response("OTP verified successfully", status=HTTP_200_OK)
            return Response("OTP does not match", status=HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ResetPasswordAPIView(CreateAPIView):
    """
    API for Mobile password reset
    """
    serializer_class = MobileResetPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data
        phone_number = data.get("phone_number", None)
        user_obj = User.objects.get(phone_number=phone_number)
        serializer = MobileResetPasswordSerializer(data=data, context={'user': user_obj})
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        if serializer.is_valid(raise_exception=True):
            return Response("Password has successfully updated", status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class UserReportLocationListAPIView(APIView):
    """
    List users location wise details
    """

    permission_classes = [AllowAny]

    def get(self, request, country, format=None):
        """
        Return a list of country or location details.
        """

        city = self.request.query_params.get('city', None)
        province = self.request.query_params.get('province', None)
        location_details = []
        try:
            if city and province:
                location = UserReport.objects.filter(user__country=country,
                                                     user__state=province, user__city=city)
            elif city or province:
                if city:
                    location = UserReport.objects.filter(user__country=country, user__city=city)
                else:
                    location = UserReport.objects.filter(user__country=country,
                                                         user__state=province)
            else:
                location = UserReport.objects.filter(user__country=country)
            if location:
                seralizer = UserReportListSerializer(location, many=True)
                location_detail = {"count": location.values_list('user').distinct().count(), 'details': seralizer.data}
                location_details.append(location_detail)
        except UserReport.DoesNotExist:
            pass
        return Response(location_details)


class SendMobileNumberOTPAPIView(CreateAPIView):
    """
    API for sending mobile OTP
    """
    serializer_class = MobilesNumberSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        user_obj = None
        data = request.data
        serializer = MobilesNumberSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            email = data.get('email')
            mobile_number = data.get('mobile_number')
            user = User.objects.filter(email=email).distinct()
            if user.exists() and user.count() == 1:
                user_obj = user.first()
            else:
                return Response('No user found for email %s' % email, status=HTTP_400_BAD_REQUEST)
            user_obj.phone_number = mobile_number
            user_obj.save()
            otp = self.generate_otp()
            if MobileOtp.objects.filter(user=user_obj).exists():
                otp_obj = MobileOtp.objects.filter(user=user_obj).first()
                otp_obj.otp = otp
                otp_obj.save()
                last_updated = Lastupdated(updated_time=timezone.now())
                last_updated.save()
            else:
                otp_obj = MobileOtp.objects.create(user=user_obj, otp=otp)
            message = "Your verification code is %s" % otp
            to = mobile_number
            send_twilio_sms.delay(message, to)
            return Response({"msg": "Message sent successfully", "status": 200})

    def generate_otp(self):
        otp = randint(1000, 9999)
        return otp


class StatusCreateAPIView(ListCreateAPIView):
    """
    Status Detail Create APIView
    """
    serializer_class = StatusSerializer
    queryset = Status.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Status.objects.all()

    def perform_create(self, serializer):
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        serializer.save()


class LastUpdatedAPIView(APIView):
    """
    List Diseases
    """

    permission_classes = [AllowAny]

    def get(self, request, format=None):
        last = Lastupdated.objects.order_by('-updated_time').first()
        seralizer = LastUpdatedListSerializer(last)
        return Response(seralizer.data)


class UserTestingCreateAPIView(ListCreateAPIView):
    """
    User Testing Detail Create APIView
    """
    serializer_class = UserTestingSerializer
    queryset = UserTesting.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return UserTesting.objects.filter(user=user).order_by('-tested_date')

    def create(self, request, *args, **kwargs):
        user = self.request.user
        last_testing = UserTesting.objects.filter(user=self.request.user).last()
        data = request.data
        user.last_updated = timezone.now()
        user.is_tested = True
        test_result = data.get('test_result')
        tested_date = datetime.datetime.strptime(data.get('tested_date'), "%Y-%m-%d").date()
        if last_testing is None and test_result == 'Positive':
            user.risk_level = True
        elif last_testing is not None and last_testing.tested_date < tested_date and test_result == 'Positive':
            user.risk_level = True
        else:
            user.risk_level = False
        user.save()
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        report = UserReport.objects.filter(user=self.request.user).last()
        if last_testing is not None:
            testing_number = re.search(r'\d+', last_testing.name)
            if testing_number is not None:
                number = int(testing_number.group()) + 1
                name = 'Testing R' + str(number)
            else:
                name = 'Testing R1'
        else:
            name = 'Testing R1'
        serializer = UserTestingSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save(user=self.request.user, name=name)
            data = serializer.data
            if report:
                report.is_tested = True
                report.testing_id = data['id']
                report.test_result = data['test_result']
                report.save()
            headers = self.get_success_headers(serializer.data)
            return Response(data, status=status.HTTP_201_CREATED, headers=headers)


class UpdateUserTestingDetails(RetrieveUpdateAPIView):
    """
    View to retrieve patch update vaccine details
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserTestingUpdateSerializer

    def get_object(self):
        user = self.request.user
        user.last_updated = timezone.now()
        user.save()
        testing_id = self.kwargs["testing_id"]
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        return UserTesting.objects.get(id=testing_id)


class UserTestingDeleteView(DestroyAPIView):
    """
    Delete vaccine instance
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserTestingSerializer

    def get_object(self):
        user = self.request.user
        user.last_updated = timezone.now()
        user.save()
        report = UserReport.objects.filter(user=self.request.user).last()
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        testing_id = self.kwargs["testing_id"]
        return get_object_or_404(UserTesting.objects.all(), pk=testing_id)


class ScreeningViewSet(viewsets.ModelViewSet):
    queryset = Screening.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ScreeningDetailSerializer
        return ScreeningSerializer


class ScreeningQuestionViewSet(viewsets.ModelViewSet):
    queryset = ScreeningQuestion.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ScreeningQuestionDetailSerializer
        return ScreeningQuestionSerializer


class ScreeningQuestionOptionViewSet(viewsets.ModelViewSet):
    queryset = ScreeningQuestionOption.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ScreeningQuestionOptionSerializer


class ScreeningUserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ScreeningUser.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ScreeningUserDetailSerializer
        return ScreeningUserSerializer

    @action(detail=False, methods=['get'])
    def get_last_result(self, request):
        try:
            last_screening_user = request.user.screening_users.latest('answered_at')
            return Response(last_screening_user.status, status=status.HTTP_200_OK)
        except ScreeningUser.DoesNotExist:
            return Response('User has no screenings yet', status=status.HTTP_400_BAD_REQUEST)


class ScreeningAnswerViewSet(viewsets.ModelViewSet):
    queryset = ScreeningAnswer.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ScreeningAnswerSerializer
