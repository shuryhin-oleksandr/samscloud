import json
from rest_framework import pagination

from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model

from random import randint

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode
from django_rest_passwordreset.views import ResetPasswordConfirm, ResetPasswordRequestToken
from django_rest_passwordreset.models import ResetPasswordToken
from rest_framework.views import APIView

from apps.organization.models import OrganizationProfile, EmergencyContact
from django.db.models import Q

from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    UpdateAPIView,
    RetrieveAPIView,
    DestroyAPIView, RetrieveUpdateAPIView, get_object_or_404, ListCreateAPIView
)

from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAdminUser,
    IsAuthenticatedOrReadOnly,
)
from apps.accounts.api.serializers import (UserCreateSerializer,
                                           UserLoginSerializer,
                                           UserListSerializer,
                                           UserDetailUpdateSerializer,
                                           UserEmailSerializer,
                                           ResetPasswordSerializer,
                                           UserActivationSerializer,
                                           UserEmailCheckSerializer,
                                           MobileNumberSerializer,
                                           MobileOTPSerializer,
                                           ProfilePicSerializer,
                                           CustomPasswordTokenSerializer,
                                           UserResetPasswordSerializer,
                                           MobileForgotPasswordSerializer,
                                           FCMDeviceSerializer,
                                           MobileResetPasswordSerializer,
                                           EmergencyContactAddSerializer,
                                           EmergencyContactActivateSerializer,
                                           EmergencyContactDeleteSerializer,
                                           EmergencyContactDetailsSerializer,
                                           UsersListSerializer,
                                           EmergencyContactRequestCheckinSerializer,
                                           ContactLocationUpdateerializer, UserProfileSerializer, UserDetailsSerializer,
                                           UserNotificationSerializer, UserCurrentLocationSerializer,
                                           ShareLocationSerializer, UserSettingsSerializer,
                                           NotificationHistorySerializer)

from fcm_django.models import FCMDevice

from .utils import send_emergency_contact_status, send_push_notification, send_incident_end_report
from ..models import MobileOtp, ForgotPasswordOTP
from apps.accounts.api.utils import get_tokens_for_user, send_account_activation_email, \
    send_password_reset_confirm_email, send_twilio_sms
from apps.organization.models import OrganizationProfile, UserOrganization
from ...reports.api.serializers import UserGeoFenceSerializer, ListUserGeoFenceSerializer, \
    UserGeoFenceSActivateSerializer, HideGeofenceSerializer, GeofenceResponderAlertSerializer, \
    HideGeofenceCheckinSerializer
from ...reports.models import NotificationSettings, CurrentUserLocation, NotificationHistory, UserGeofences, \
    UserGeofenceStatus

User = get_user_model()


class UserCreateAPIView(CreateAPIView):
    """
    User Register APIView
    """
    serializer_class = UserCreateSerializer
    queryset = User.objects.all()
    permission_classes = [AllowAny]


class UserActivationAPIView(CreateAPIView):
    """
    User activation APIView. Used in forgot password
    """
    permission_classes = [AllowAny]
    serializer_class = UserActivationSerializer

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = UserActivationSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            uidb64 = data.get('uidb64')
            token = data.get('token')
            pro_code = data.get('pro_code')
            password = data.get('password')
            try:
                uid = urlsafe_base64_decode(uidb64).decode()
                user = User.objects.get(pk=uid)
            except User.DoesNotExist:
                user = None
            if user and default_token_generator.check_token(user, token) and not user.is_verified:
                user_organization_id = None
                user.is_verified = True
                user.is_active = True
                user.set_password(password)
                user.save()
                send_password_reset_confirm_email(request, user)
                try:
                    organization_obj = OrganizationProfile.objects.get(pro_code=pro_code)
                    if not UserOrganization.objects.filter(user=user, organization=organization_obj).exists():
                        UserOrganization.objects.create(user=user, organization=organization_obj)
                    user_organization_id = organization_obj.id
                except:
                    return Response("Organization does not exists", status=HTTP_400_BAD_REQUEST)
                response_token = get_tokens_for_user(user)
                data = {}
                data['token'] = response_token.get('access', None)
                data['refresh_token'] = response_token.get('refresh', None)
                data['id'] = user.id
                data['organization_id'] = user_organization_id
                return Response(data, status=HTTP_200_OK)
            else:
                return Response('Activation link expired', status=HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ResendUserActivationAPIView(CreateAPIView):
    """
    Resend forgot password email APIView
    """
    permission_classes = [AllowAny]
    serializer_class = UserEmailCheckSerializer

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = UserEmailCheckSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            email = serializer.validated_data.get('email')
            user_obj = User.objects.get(email=email)
            if not (user_obj.is_verified and user_obj.is_active):
                send_account_activation_email(request, user_obj)
                return Response('Please check your email', status=HTTP_200_OK)
            else:
                return Response('User is already verified', status=HTTP_400_BAD_REQUEST)
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


class UserListAPIView(ListAPIView):
    """
    User List APIView
    """
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated]
    queryset = User.objects.filter(is_superuser=False)


class UserUpdateAPIView(UpdateAPIView):
    """
    Update user details APIView
    """
    serializer_class = UserDetailUpdateSerializer
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()

    def partial_update(self, request, *args, **kwargs):
        user_obj = self.get_object()
        serializer = UserDetailUpdateSerializer(user_obj, data=request.data,
                                                partial=True)  # set partial=True to update a data partially
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)



class UserDetailAPIView(RetrieveAPIView):
    """
    Ger User detail APIView
    """
    serializer_class = UserDetailUpdateSerializer
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()
    lookup_field = 'pk'


class IsEmailExistsAPIView(CreateAPIView):
    """
    Check whether is email exists or not.
    """
    permission_classes = [AllowAny]
    serializer_class = UserEmailSerializer

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = UserEmailSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            new_data = serializer.data
            return Response(new_data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ResetPasswordAPIView(CreateAPIView):
    """
    Reset Password APIView
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ResetPasswordSerializer

    def post(self, request, *args, **kwargs):
        data = request.data
        user_obj = request.user
        serializer = ResetPasswordSerializer(data=data, context={"user": user_obj})
        if serializer.is_valid(raise_exception=True):
            new_data = {'message': 'Password updated'}
            return Response(new_data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class SendMobileNumberOTPAPIView(CreateAPIView):
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
            else:
                otp_obj = MobileOtp.objects.create(user=user_obj, otp=otp)
            message = "Your verification code is %s" % otp
            to = mobile_number
            send_twilio_sms.delay(message, to)
            return Response({"msg": "Message sent successfully", "status": 200})

    def generate_otp(self):
        otp = randint(1000, 9999)
        return otp


class VerifyMobileOTPAPIView(CreateAPIView):
    """
    API for mobile OTP verification
    """
    serializer_class = MobileOTPSerializer

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = MobileOTPSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            email = data.get('email')
            otp = data.get('otp')
            user = User.objects.filter(email=email).distinct()
            if user.exists() and user.count() == 1:
                user_obj = user.first()
            else:
                return Response('No user found for email %s' % email, status=HTTP_400_BAD_REQUEST)
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
                if not (user_obj.is_active and (user_obj.is_verified or user_obj.is_phone_number_verified)):
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


class CustomResetPasswordConfirm(ResetPasswordConfirm):
    """
    Forgot password API
    """
    serializer_class = CustomPasswordTokenSerializer

    def post(self, request, *args, **kwargs):
        reset_password_token = ResetPasswordToken.objects.filter(key=request.data.get('token')).first()
        if reset_password_token:
            user = reset_password_token.user
            resp = super(CustomResetPasswordConfirm, self).post(request, *args, **kwargs)
            if resp.status_code == 200:
                send_password_reset_confirm_email(request, user)
                return Response('Your password has been successfully reset',
                                status=HTTP_200_OK)
        else:
            return Response('Your Link expired', status=HTTP_200_OK)
        return resp


class CustomResetPasswordRequestToken(ResetPasswordRequestToken):
    """
    API for sending password recovery Token
    """

    def post(self, request, *args, **kwargs):
        resp = super(CustomResetPasswordRequestToken, self).post(request, *args, **kwargs)
        if resp.status_code == 200:
            return Response('Please check your email and follow the instructions to recover your password.',
                            status=HTTP_200_OK)
        return resp


class AddProfilePicAPIView(CreateAPIView):
    """
    API to post profile picture
    """
    serializer_class = ProfilePicSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = ProfilePicSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            new_data = serializer.data
            return Response(new_data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class UserResetPasswordAPIView(CreateAPIView):
    """
    API for profile page password reset
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserResetPasswordSerializer

    def post(self, request, *args, **kwargs):
        data = request.data
        user_obj = request.user
        serializer = UserResetPasswordSerializer(data=data, context={"user": user_obj})
        if serializer.is_valid(raise_exception=True):
            new_data = {'message': 'Password updated'}
            return Response(new_data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class MobileForgotPasswordAPIView(CreateAPIView):
    """
    API for sending mobile forgot password verification
    """
    permission_classes = [AllowAny]
    serializer_class = MobileForgotPasswordSerializer

    def generate_otp(self):
        otp = randint(1000, 9999)
        return otp

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = MobileForgotPasswordSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            email = data.get("email", None)
            user_obj = User.objects.get(email=email)
            otp = self.generate_otp()
            otp_obj, created = ForgotPasswordOTP.objects.get_or_create(user=user_obj)
            otp_obj.otp = otp
            otp_obj.save()
            message = "Your verification code is %s" % otp
            to = user_obj.phone_number
            send_twilio_sms.delay(message, to)
            return Response("An OTP has been sent to %s" % (user_obj.phone_number), status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class MobileForgotPasswordVerifyAPIView(CreateAPIView):
    """
    API for Mobile forgot password verification
    """
    serializer_class = MobileForgotPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = MobileForgotPasswordSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            email = data.get("email", None)
            otp = data.get("otp", None)
            user_obj = User.objects.get(email=email)
            otp_obj = ForgotPasswordOTP.objects.get(user=user_obj)
            if otp_obj.otp == otp:
                return Response("OTP verified successfully", status=HTTP_200_OK)
            return Response("OTP does not match", status=HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class MobileResetPasswordAPIView(CreateAPIView):
    """
    API for Mobile password reset
    """
    serializer_class = MobileResetPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data
        email = data.get("email", None)
        user_obj = User.objects.get(email=email)
        serializer = MobileResetPasswordSerializer(data=data, context={'user': user_obj})
        if serializer.is_valid(raise_exception=True):
            return Response("Password has successfully updated", status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class FCMDeviceCreateAPIView(CreateAPIView):
    """
    API to create FCM tokens
    """
    serializer_class = FCMDeviceSerializer
    permission_classes = [IsAuthenticated]
    queryset = FCMDevice.objects.all()


class FCMUpdateAPIView(UpdateAPIView):
    serializer_class = FCMDeviceSerializer
    permission_classes = [IsAuthenticated]
    queryset = FCMDevice.objects.all()


class EmergencyContactCheckinAPIView(CreateAPIView):
    serializer_class = EmergencyContactRequestCheckinSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        serializer = EmergencyContactRequestCheckinSerializer(data=data, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            contact_id = request.data['contact_id']
            current_usr = request.user
            user_obj = None
            contact_obj = EmergencyContact.objects.filter(id=contact_id)
            if contact_obj[0].email is not None:
                user_obj = User.objects.filter(email=contact_obj[0].email)
            elif contact_obj[0].phone_number is not None:
                user_obj = User.objects.filter(phone_number=contact_obj[0].phone_number)
            if user_obj is not None:
                qs = FCMDevice.objects.filter(user=user_obj[0])
                if qs.exists():
                    fcm_obj = qs.first()
                    data = {
                        "type": "request-check-in",
                        "contact": contact_obj[0].id
                    }
                    message = "%s is requesting a check-in" % (
                    current_usr.first_name)
                    title = "Request to checkIn"
                    send_push_notification.delay(fcm_obj.id, title, message, data)
                    ser = EmergencyContactAddSerializer(contact_obj[0])
                    histroy = NotificationHistory(user=user_obj.first(), requested_user=current_usr, attribute=ser.data,
                                        notification_type="request-check-in", message=message,
                                        title=title)
                    histroy.save()
                return Response({'status': 'Success'}, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ContactLocationUpdateAPIView(CreateAPIView):
    serializer_class = ContactLocationUpdateerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        serializer = ContactLocationUpdateerializer(data=data, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            contact_id = request.data['contact_id']
            checkin_status = request.data['checkin_status']

            current_usr = request.user
            contact_obj = EmergencyContact.objects.get(id=contact_id)
            if checkin_status == 'Accepted':
                latitude = request.data['latitude']
                longitude = request.data['longitude']
                address = request.data['address']
                contact_obj.latitude = latitude
                contact_obj.longitude = longitude
                contact_obj.request_checkin_updated = timezone.now()
                contact_obj.request_checkin_latitude = latitude
                contact_obj.request_checkin_longitude = longitude
                contact_obj.request_checkin_address = address
                contact_obj.save()
            if current_usr is not None:
                qs = FCMDevice.objects.filter(user=contact_obj.user)
                if qs.exists():
                    fcm_obj = qs.first()
                    data = {
                        "type": "contact-location-update",
                    }
                    message = "%s has %s your check-in request" % (
                    contact_obj.name, checkin_status)
                    title = "checkIn response"
                    histroy = NotificationHistory(user=contact_obj.user, requested_user=request.user,
                                                  notification_type="contact-location-update",
                                                  message=message,
                                                  title=title)
                    histroy.save()
                    send_push_notification.delay(fcm_obj.id, title, message, data)
            return Response({'status': 'Success'}, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)



class EmergencyContactAddView(CreateAPIView):
    serializer_class = EmergencyContactAddSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = EmergencyContactAddSerializer(data=data, context={'request': request}, many=True)
        if serializer.is_valid(raise_exception=True):
            serializer.create(validated_data=data)
            phone_nos = [d['phone_number'] for d in data if 'phone_number' in d]
            mail_ids = [d['email'] for d in data if 'email' in d and 'phone_number' not in d]
            objs = EmergencyContact.objects.filter(
                Q(user=request.user, phone_number__in=phone_nos) | Q(user=request.user, email__in=mail_ids))
            new_data = EmergencyContactAddSerializer(objs, many=True).data
            return Response(new_data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class EmergencyContactListAPIView(ListAPIView):
    serializer_class = EmergencyContactAddSerializer
    queryset = EmergencyContact.objects.all()
    permission_classes = [IsAuthenticated]


class EmergencyContactActivateAPIView(CreateAPIView):
    serializer_class = EmergencyContactActivateSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = EmergencyContactActivateSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            contact_obj = EmergencyContact.objects.get(uuid=request.data['uuid'])
            contact_obj.status = request.data['status']
            if 'latitude' in request.data and 'longitude' in request.data:
                contact_obj.latitude = request.data['latitude']
                contact_obj.longitude = request.data['longitude']
            contact_obj.save()
            newdata = EmergencyContactActivateSerializer(contact_obj).data

            if request.data['status'] == "Accepted":
                message = "%s has accepted your request." % (
                    contact_obj.name)
            else:
                message = "%s has declined your request." % (
                    contact_obj.name)
            try:
                fcm_obj = FCMDevice.objects.get(user=contact_obj.user)
                title = "Incident Reporting"
                data = {}
                data["action"] = 'emergency_contact_response'
                if contact_obj.phone_number and contact_obj.phone_number != "":
                    user = User.objects.filter(Q(email=contact_obj.email) | Q(phone_number=contact_obj.phone_number)).first()
                else:
                    user = User.objects.filter(Q(email=contact_obj.email)).first()
                if user:
                    histroy = NotificationHistory(user=contact_obj.user, requested_user=user,
                                                  attribute=newdata,
                                                  notification_type="emergency_contact_response", message=message,
                                                  title=title)
                    histroy.save()
                else:
                    histroy = NotificationHistory(user=contact_obj.user,
                                                  attribute=newdata,
                                                  notification_type="emergency_contact_response", message=message,
                                                  title=title)
                    histroy.save()
                send_push_notification.delay(fcm_obj.id, title, message, data)
            except ObjectDoesNotExist:
                pass
            to = contact_obj.user.phone_number
            send_twilio_sms.delay(message, to)
            send_emergency_contact_status(contact_obj.user.email, contact_obj.user.first_name, contact_obj.name,
                                          request.data['status'])
            return Response(newdata, status=HTTP_200_OK)
        else:
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class EmergencyContactDeleteAPIView(DestroyAPIView):
    queryset = EmergencyContact.objects.all()
    serializer_class = EmergencyContactDeleteSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        if serializer.is_valid:
            user_bj = User.objects.filter(Q(email=instance.email) | Q(phone_number=instance.phone_number)).first()
            if user_bj:
                histroy = NotificationHistory.objects.filter(user=user_bj, requested_user=self.request.user)
                histroy.delete()
            self.perform_destroy(instance)
            data = {
                "status": "true",
                "message": "Emergency Contact is deleted successfully"
                }
            return Response(data, status=HTTP_200_OK)
        else:
            return Response({"status": "false"}, status=HTTP_404_NOT_FOUND)


class EmergencyContactDetailsListAPIView(ListAPIView):
    serializer_class = EmergencyContactDetailsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self, *args, **kwargs):
        contact_type = self.request.query_params.get('type', None)
        if contact_type:
            return EmergencyContact.objects.filter(user=self.request.user, contact_type=contact_type)
        return EmergencyContact.objects.filter(user=self.request.user)


class UserPhoneListAPIView(CreateAPIView):
    serializer_class = UsersListSerializer
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()

    def post(self, request, *args, **kwargs):
        nums = list(map(lambda num: num['phone_no'], request.data))
        users = User.objects.filter(phone_number__in=nums)
        serializer = UsersListSerializer(users, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

class UserUpdateProfileAPIView(RetrieveUpdateAPIView):
    """
    View to retrieve patch update user details
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return User.objects.get(id=self.request.user.id)

class UserDetailListAPIView(ListAPIView):
    """
    user  wise details
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserDetailsSerializer

    def get_queryset(self, *args, **kwargs):
        return User.objects.filter(id=self.request.user.id)

class UserNotificationsAPIView(RetrieveAPIView):
    """
    user  notification details
    """

    permission_classes = [IsAuthenticated]

    # def get_queryset(self, *args, **kwargs):
    #     return NotificationSettings.objects.get(user=self.request.user)
    def get(self, request, format=None):
        """
        Return a list of global effects.
        """

        filter_data = NotificationSettings.objects.get(user=self.request.user)
        seralizer = UserNotificationSerializer(filter_data)
        return Response(seralizer.data)

class UserNotificationUpdateAPIView(RetrieveUpdateAPIView):
    """
    View to retrieve patch update user notification settings
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserNotificationSerializer

    def get_object(self):
        return NotificationSettings.objects.get(user=self.request.user)

class CurrentLocationAPIView(RetrieveUpdateAPIView):
    """
    View to retrieve patch update user current location
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserCurrentLocationSerializer

    def get_object(self):
        return CurrentUserLocation.objects.get(user=self.request.user)

    def put(self,request):
        try:
            snippet = CurrentUserLocation.objects.get(user=self.request.user)
            serializer = UserCurrentLocationSerializer(data=request.data)
            if serializer.is_valid():
                serializer.update(snippet,validated_data=serializer.data)
                return Response(serializer.data, status=HTTP_200_OK)
        except Exception as e:
            print e


class ShareLocationAPIView(RetrieveUpdateAPIView):
    """
    View to retrieve patch update user current location
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ShareLocationSerializer

    def get_object(self):
        return CurrentUserLocation.objects.get(user=self.request.user)

    def patch(self, request, *args, **kwargs):
        user_obj = self.request.user
        if request.data['share_location'] == True:
            emergency_contacts_qs = EmergencyContact.objects.filter(user=user_obj, status="Accepted",
                                                                    contact_type='Emergency')
            if emergency_contacts_qs.exists():
                for contact_user in emergency_contacts_qs:
                    if User.objects.filter(
                            Q(email=contact_user.email) | Q(phone_number=contact_user.phone_number)).first():
                        user_bj = User.objects.filter(
                            Q(email=contact_user.email) | Q(phone_number=contact_user.phone_number)).first()
                        setting = NotificationSettings.objects.filter(user=user_bj).first()
                        try:
                            user = User.objects.get(email=contact_user.email)
                            if setting.contact_disable_location == True:
                                fcm_obj = FCMDevice.objects.get(user=user)
                                title = "Share Location Status"
                                message = "%s has been start sharing location." % (
                                    user_obj.first_name)
                                data = {
                                        "action": "share-loaction",
                                        "type": "share_location"
                                }
                                histroy = NotificationHistory(user=user_bj, requested_user=user_obj,
                                                              notification_type="share-loaction",
                                                              message=message,
                                                              title=title)
                                histroy.save()
                                send_push_notification.delay(fcm_obj.id, title, message, data)
                        except ObjectDoesNotExist:
                            pass
        else:
            emergency_contacts_qs = EmergencyContact.objects.filter(user=user_obj, status="Accepted",
                                                                    contact_type='Emergency')
            if emergency_contacts_qs.exists():
                for contact_user in emergency_contacts_qs:
                    if User.objects.filter(
                            Q(email=contact_user.email) | Q(phone_number=contact_user.phone_number)).first():
                        user_bj = User.objects.filter(
                            Q(email=contact_user.email) | Q(phone_number=contact_user.phone_number)).first()
                        setting = NotificationSettings.objects.filter(user=user_bj).first()
                        try:
                            user = User.objects.get(email=contact_user.email)
                            if setting.contact_disable_location == True:
                                fcm_obj = FCMDevice.objects.get(user=user)
                                title = "Share Location Status"
                                message = "%s has been stop sharing location." % (
                                    user_obj.first_name)
                                data = {
                                    "action": "share-loaction",
                                    "type": "share_location"
                                }
                                histroy = NotificationHistory(user=user_bj, requested_user=user_obj,
                                                              notification_type="share-loaction",
                                                              message=message,
                                                              title=title)
                                histroy.save()
                                send_push_notification.delay(fcm_obj.id, title, message, data)
                        except ObjectDoesNotExist:
                            pass
                    #     if contact_user.phone_number and contact_user.phone_number != "" and setting.send_incident_text:
                    #         message = "%s has been sharing his location." % (
                    #             user_obj.first_name)
                    #         to = contact_user.phone_number
                    #         send_twilio_sms.delay(message, to)
                    #     if contact_user.email and contact_user.email != "" and setting.send_incident_email:
                    #         send_incident_end_report(contact_user.email, contact_user.name, user_obj, reason)
                    # else:
                    #     if contact_user.phone_number and contact_user.phone_number != "":
                    #         message = "%s has been sharing his location." % (
                    #             user_obj.first_name)
                    #         to = contact_user.phone_number
                    #         send_twilio_sms.delay(message, to)
                    #     if contact_user.email and contact_user.email != "":
                    #         send_incident_end_report(contact_user.email, contact_user.name, user_obj, reason)
        return self.partial_update(request, *args, **kwargs)

class UserSettingsAPIView(RetrieveAPIView):
    """
    user  settings details
    """

    permission_classes = [IsAuthenticated]

    # def get_queryset(self, *args, **kwargs):
    #     return NotificationSettings.objects.get(user=self.request.user)
    def get(self, request, format=None):
        """
        Return a list of settings preference.
        """

        filter_data = NotificationSettings.objects.get(user=self.request.user)
        seralizer = UserSettingsSerializer(filter_data)
        return Response(seralizer.data)

class UserSettingsUpdateAPIView(RetrieveUpdateAPIView):
    """
    View to retrieve patch update user settings
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserSettingsSerializer

    def get_object(self):
        return NotificationSettings.objects.get(user=self.request.user)


class ListNotificationAPIView(ListAPIView):
    """
    user  notification list
    """

    permission_classes = [IsAuthenticated]
    serializer_class = NotificationHistorySerializer
    pagination_class = pagination.LimitOffsetPagination

    def get_queryset(self, *args, **kwargs):
        return NotificationHistory.objects.filter(user=self.request.user).order_by('-date_created')

class DeleteNotificationAPIView(DestroyAPIView):
    """
    Delete notification instance
    """

    permission_classes = [IsAuthenticated]
    serializer_class = NotificationHistorySerializer

    def get_object(self):
        notification_id = self.kwargs["notification_id"]
        contact = get_object_or_404(NotificationHistory.objects.all(), pk=notification_id)
        return contact

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        if serializer.is_valid:
            self.perform_destroy(instance)
            data = {
                "status": "true",
                "message": "Incident is deleted successfully"
                }
            return Response(data, status=HTTP_200_OK)
        else:
            return Response({"status": "false"}, status=HTTP_404_NOT_FOUND)

class GeoFenceListCreateAPIView(ListCreateAPIView):
    """
    API for create and list incidents
    """
    serializer_class = UserGeoFenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserGeofences.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class UpdateGeoFenceDetails(RetrieveUpdateAPIView):
    """
    View to retrieve patch update geofence details
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserGeoFenceSerializer

    def get_object(self):
        geofence_id = self.kwargs["geofence_id"]
        return UserGeofences.objects.get(id=geofence_id)

class DeleteGeoFenceDetails(DestroyAPIView):
    """
    Delete geofence instance
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserGeoFenceSerializer

    def get_object(self):
        geofence_id = self.kwargs["geofence_id"]
        geofence = get_object_or_404(UserGeofences.objects.all(), pk=geofence_id, user=self.request.user)
        return geofence

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        if serializer.is_valid:
            self.perform_destroy(instance)
            data = {
                "status": "true",
                "message": "Geofence is deleted successfully"
                }
            return Response(data, status=HTTP_200_OK)
        else:
            return Response({"status": "false"}, status=HTTP_404_NOT_FOUND)

class ListManagingGeoFences(ListAPIView):
    """
    user  notification list
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ListUserGeoFenceSerializer

    def get_queryset(self, *args, **kwargs):
        return UserGeofences.objects.filter(user=self.request.user).order_by('-date_created')

class ListAssignedGeoFences(ListAPIView):
    """
    user  notification list
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ListUserGeoFenceSerializer

    def get_queryset(self, *args, **kwargs):
        emergency = EmergencyContact.objects.filter(
                Q(phone_number=self.request.user.phone_number) | Q(email=self.request.user.email))
        ids =[]
        for contact in emergency:
            ids.append(contact.id)
        return UserGeofences.objects.filter(Q(assign_contacts__in=ids) | Q(assign_mangers__in=ids)).order_by('-date_created')

class UserGeofenceStatusActivateAPIView(CreateAPIView):
    serializer_class = UserGeoFenceSActivateSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = UserGeoFenceSActivateSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            contact_obj = EmergencyContact.objects.get(id=int(request.data['emergency_id']))
            type = request.data['type']
            user = User.objects.filter(
                Q(phone_number=contact_obj.phone_number) | Q(email=contact_obj.email))
            if request.data['status'] == "Accepted":
                message = "%s has accepted your request." % (
                    contact_obj.name)
                if type == 'Contact':
                    geofence_obj = UserGeofences.objects.filter(id=int(request.data['geofence_id']),
                                                                assign_contacts__id=contact_obj.id)
                    if user:

                        status = UserGeofenceStatus(user=user.first(), geofence=geofence_obj.first(), emergency=contact_obj, status=request.data['status'],
                                                   contact_type=type)
                        status.save()
                    else:
                        status = UserGeofenceStatus(geofence=geofence_obj.first(), emergency=contact_obj,
                                                    status=request.data['status'],
                                                    contact_type=type)
                        status.save()
                if type == 'Manager':
                    geofence_obj = UserGeofences.objects.filter(id=int(request.data['geofence_id']),
                                                                assign_mangers__id=contact_obj.id)
                    if user:
                        status = UserGeofenceStatus(user=user.first(), geofence=geofence_obj.first(),
                                                    emergency=contact_obj, status=request.data['status'],
                                                    contact_type=type)
                        status.save()
                    else:
                        status = UserGeofenceStatus(geofence=geofence_obj.first(),
                                                    emergency=contact_obj, status=request.data['status'],
                                                    contact_type=type)
                        status.save()
            else:
                message = "%s has declined your request." % (
                    contact_obj.name)
                if type == 'Contact':
                    geofence_obj = UserGeofences.objects.filter(id=int(request.data['geofence_id']),
                                                                assign_contacts__id=contact_obj.id).first()
                    geofence_obj.assign_contacts.remove(contact_obj)
                    if user:
                        status = UserGeofenceStatus(user=user.first(), geofence=geofence_obj, emergency=contact_obj, status=request.data['status'],
                                                   contact_type=type)
                        status.save()
                    else:
                        status = UserGeofenceStatus(geofence=geofence_obj,
                                                    emergency=contact_obj, status=request.data['status'],
                                                    contact_type=type)
                        status.save()

                if type == 'Manager':
                    geofence_obj = UserGeofences.objects.filter(id=int(request.data['geofence_id']),
                                                                assign_mangers__id=contact_obj.id).first()
                    geofence_obj.assign_mangers.remove(contact_obj)
                    if user:
                        status = UserGeofenceStatus(user=user.first(), geofence=geofence_obj,
                                                    emergency=contact_obj, status=request.data['status'],
                                                    contact_type=type)
                        status.save()
                    else:
                        status = UserGeofenceStatus(geofence=geofence_obj,
                                                    emergency=contact_obj, status=request.data['status'],
                                                    contact_type=type)
                        status.save()
            try:
                fcm_obj = FCMDevice.objects.get(user=contact_obj.user)
                title = "Accept or Reject Geo Fence"
                data = {}
                data["action"] = 'geofence_contact_response'
                user = User.objects.filter(
                    Q(phone_number=contact_obj.phone_number) | Q(email=contact_obj.user.email))
                if user:
                    histroy = NotificationHistory(user=contact_obj.user, requested_user=user.first(),
                                                  attribute=serializer.data,
                                                  notification_type="geofence_contact_response", message=message,
                                                  title=title)
                    histroy.save()
                else:
                    histroy = NotificationHistory(user=contact_obj.user,
                                                  attribute=serializer.data,
                                                  notification_type="geofence_contact_response", message=message,
                                                  title=title)
                    histroy.save()
                send_push_notification.delay(fcm_obj.id, title, message, data)
            except ObjectDoesNotExist:
                pass
            return Response(serializer.data, status=HTTP_200_OK)
        else:
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

class HideGeofenceAPIView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = HideGeofenceSerializer

    def get_object(self):
        geofence_id = self.kwargs["geofence_id"]
        type = self.kwargs["type"]
        geofence = get_object_or_404(UserGeofences.objects.all(), pk=geofence_id)
        return UserGeofenceStatus.objects.get(user=self.request.user, geofence=geofence, contact_type=type)

class SendGeofenceNotificationAPIView(CreateAPIView):
    """
    API to send alert notification to responders
    """
    serializer_class = GeofenceResponderAlertSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_obj = request.user
        if GeofenceResponderAlertSerializer(data=request.data).is_valid(raise_exception=True):
            pass
        geofence = UserGeofences.objects.get(id=request.data.get("geofence_id"))
        user_geofence = UserGeofenceStatus.objects.filter(user=user_obj, status="Accepted",
                                                               contact_type=request.data.get("contact_type"), geofence=geofence)
        if user_geofence.exists():
            user_status = user_geofence.first()
            if user_status.is_hidden == False:
                qs = FCMDevice.objects.filter(
                    Q(user__email=geofence.user.email) | Q(user__phone_number=geofence.user.phone_number))
                if User.objects.filter(Q(email=geofence.user.email) | Q(phone_number=geofence.user.phone_number)).first():
                    user_bj = User.objects.filter(Q(email=geofence.user.email) | Q(phone_number=geofence.user.phone_number)).first()
                    if qs.exists():
                        fcm_obj = qs.first()
                        data = ListUserGeoFenceSerializer(geofence).data
                        message = "%s %s %s" % (user_obj.first_name, request.data.get("geofence_status"), geofence.name)
                        title = "Geo Fence Reporting"
                        histroy = NotificationHistory(user=user_bj, requested_user=user_obj,
                                                       attribute=json.dumps(data, default=str),
                                                      notification_type="geofence_alert", message=message,
                                                      title=title)
                        histroy.save()
                        data["action"] = 'geofence_alert'
                        send_push_notification.delay(fcm_obj.id, title, message, data)
                    geofence_mangers = UserGeofenceStatus.objects.filter(status="Accepted",
                                                                      contact_type="Manager",
                                                                      geofence=geofence)
                    if geofence_mangers.exists():
                        for manager in geofence_mangers:
                            qs = FCMDevice.objects.filter(
                                Q(user__email=manager.user.email) | Q(user__phone_number=manager.user.phone_number))
                            if User.objects.filter(
                                    Q(email=manager.user.email) | Q(phone_number=manager.user.phone_number)).first():
                                user_bj = User.objects.filter(
                                    Q(email=manager.user.email) | Q(phone_number=manager.user.phone_number)).first()
                                setting = NotificationSettings.objects.filter(user=user_bj).first()
                                if qs.exists():
                                    fcm_obj = qs.first()

                                    data = ListUserGeoFenceSerializer(geofence).data

                                    message = "%s %s %s" % (
                                    user_obj.first_name, request.data.get("geofence_status"), geofence.name)
                                    title = "Geo Fence Reporting"
                                    histroy = NotificationHistory(user=user_bj, requested_user=user_obj,
                                                                  attribute=json.dumps(data, default=str),
                                                                  notification_type="geofence_alert", message=message,
                                                                  title=title)
                                    histroy.save()
                                    data["action"] = 'geofence_alert'
                                    send_push_notification.delay(fcm_obj.id, title, message, data)
            else:
                qs = FCMDevice.objects.filter(
                    Q(user__email=user_obj.email) | Q(user__phone_number=user_obj.phone_number))
                if User.objects.filter(
                        Q(email=user_obj.email) | Q(phone_number=user_obj.phone_number)).first():
                    user_bj = User.objects.filter(
                        Q(email=user_obj.email) | Q(phone_number=user_obj.phone_number)).first()
                    if qs.exists():
                        fcm_obj = qs.first()

                        data = ListUserGeoFenceSerializer(geofence).data

                        message = "please is check-in %s geo fence. you are %s the geo fence" % (geofence.name, request.data.get("geofence_status"))
                        title = "Geo Fence Hide Checkin"
                        histroy = NotificationHistory(user=user_bj, requested_user=user_obj,
                                                      attribute=json.dumps(data, default=str),
                                                      notification_type="geofence-hide_checkin", message=message,
                                                      title=title)
                        histroy.save()
                        user_status.request_status = request.data.get("geofence_status")
                        user_status.save()
                        data["action"] = 'geofence-hide_checkin'
                        send_push_notification.delay(fcm_obj.id, title, message, data)

        if user_geofence.exists() and user_geofence.first().is_hidden == False:
            msg = "Notifications are sent to geo fence manager contacts"
        elif user_geofence.exists() and user_geofence.first().is_hidden == True:
            msg = "User in hiden mode Notifications are sent for check-in "
        else:
            msg = "No Geo fence are found"
        data = {'message': msg}
        return Response(data, status=HTTP_200_OK)


class LeaveGeofenceAssignedUserAPIView(DestroyAPIView):
    """
    Delete geofence instance
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserGeoFenceSerializer

    def get_object(self):
        geofence_id = self.kwargs["geofence_id"]
        type = self.kwargs["type"]
        geofence = get_object_or_404(UserGeofences.objects.all(), pk=geofence_id)
        geofence_status = UserGeofenceStatus.objects.get(user=self.request.user, geofence=geofence, contact_type=type)
        return geofence_status

    def destroy(self, request, *args, **kwargs):
        user_obj = self.request.user
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        if serializer.is_valid:
            emergency = instance.emergency
            geofence = instance.geofence
            if instance.contact_type == "Manager":
                geofence.assign_mangers.remove(emergency)
            else:
                geofence.assign_contacts.remove(emergency)
            qs = FCMDevice.objects.filter(
                Q(user__email=geofence.user.email) | Q(user__phone_number=geofence.user.phone_number))
            if User.objects.filter(
                    Q(email=geofence.user.email) | Q(phone_number=geofence.user.phone_number)).first():
                user_bj = User.objects.filter(
                    Q(email=geofence.user.email) | Q(phone_number=geofence.user.phone_number)).first()
                if qs.exists():
                    fcm_obj = qs.first()
                    data = ListUserGeoFenceSerializer(geofence).data
                    message = "%s has left  %s" % (user_obj.first_name, geofence.name)
                    title = "User Left Geo Fence"
                    histroy = NotificationHistory(user=user_bj, requested_user=user_obj,
                                                  attribute=json.dumps(data, default=str),
                                                  notification_type="left_geofence", message=message,
                                                  title=title)
                    histroy.save()
                    data["action"] = 'left_geofence'
                    send_push_notification.delay(fcm_obj.id, title, message, data)
                geofence_mangers = UserGeofenceStatus.objects.filter(status="Accepted",
                                                                     contact_type="Manager",
                                                                     geofence=geofence)
                if geofence_mangers.exists():
                    for manager in geofence_mangers:
                        qs = FCMDevice.objects.filter(
                            Q(user__email=manager.user.email) | Q(user__phone_number=manager.user.phone_number))
                        if User.objects.filter(
                                Q(email=manager.user.email) | Q(phone_number=manager.user.phone_number)).first():
                            user_bj = User.objects.filter(
                                Q(email=manager.user.email) | Q(phone_number=manager.user.phone_number)).first()
                            if qs.exists():
                                fcm_obj = qs.first()

                                data = ListUserGeoFenceSerializer(geofence).data

                                message = "%s has left  %s" % (user_obj.first_name, geofence.name)
                                title = "User Left Geo Fence"
                                histroy = NotificationHistory(user=user_bj, requested_user=user_obj,
                                                              attribute=json.dumps(data, default=str),
                                                              notification_type="left_geofence", message=message,
                                                              title=title)
                                histroy.save()
                                data["action"] = 'left_geofence'
                                send_push_notification.delay(fcm_obj.id, title, message, data)
            self.perform_destroy(instance)
            data = {
                "status": "true",
                "message": "User has been removed from Geo fence successfully"
                }
            return Response(data, status=HTTP_200_OK)
        else:
            return Response({"status": "false"}, status=HTTP_404_NOT_FOUND)

class HidemodeCheckinGeofenceAPIView(CreateAPIView):
    """
    API to send alert notification to responders
    """
    serializer_class = HideGeofenceCheckinSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_obj = request.user
        if HideGeofenceCheckinSerializer(data=request.data).is_valid(raise_exception=True):
            pass
        geofence = UserGeofences.objects.get(id=request.data.get("geofence_id"))
        user_geofence = UserGeofenceStatus.objects.filter(user=user_obj, status="Accepted",
                                                               contact_type=request.data.get("contact_type"), geofence=geofence)
        if user_geofence.exists():
            user_status = user_geofence.first()
            qs = FCMDevice.objects.filter(
                Q(user__email=geofence.user.email) | Q(user__phone_number=geofence.user.phone_number))
            if User.objects.filter(Q(email=geofence.user.email) | Q(phone_number=geofence.user.phone_number)).first():
                user_bj = User.objects.filter(Q(email=geofence.user.email) | Q(phone_number=geofence.user.phone_number)).first()
                if qs.exists():
                    fcm_obj = qs.first()
                    data = ListUserGeoFenceSerializer(geofence).data
                    message = "%s %s %s" % (user_obj.first_name, user_status.request_status, geofence.name)
                    title = "Geo Fence Reporting"
                    histroy = NotificationHistory(user=user_bj, requested_user=user_obj,
                                                   attribute=json.dumps(data, default=str),
                                                  notification_type="hide_checkin_geofence", message=message,
                                                  title=title)
                    histroy.save()
                    data["action"] = 'hide_checkin_geofence'
                    send_push_notification.delay(fcm_obj.id, title, message, data)
                geofence_mangers = UserGeofenceStatus.objects.filter(status="Accepted",
                                                                  contact_type="Manager",
                                                                  geofence=geofence)
                if geofence_mangers.exists():
                    for manager in geofence_mangers:
                        qs = FCMDevice.objects.filter(
                            Q(user__email=manager.user.email) | Q(user__phone_number=manager.user.phone_number))
                        if User.objects.filter(
                                Q(email=manager.user.email) | Q(phone_number=manager.user.phone_number)).first():
                            user_bj = User.objects.filter(
                                Q(email=manager.user.email) | Q(phone_number=manager.user.phone_number)).first()
                            if qs.exists():
                                fcm_obj = qs.first()
                                data = ListUserGeoFenceSerializer(geofence).data

                                message = "%s %s %s" % (
                                user_obj.first_name, user_status.request_status, geofence.name)
                                title = "Geo Fence Reporting"
                                histroy = NotificationHistory(user=user_bj, requested_user=user_obj,
                                                              attribute=json.dumps(data, default=str),
                                                              notification_type="hide_checkin_geofence", message=message,
                                                              title=title)
                                histroy.save()
                                data["action"] = 'hide_checkin_geofence'
                                send_push_notification.delay(fcm_obj.id, title, message, data)
        if user_geofence.exists():
            msg = "Notifications are sent to geo fence manager contacts"
        else:
            msg = "No Geo fence are found associated user"
        data = {'message': msg}
        return Response(data, status=HTTP_200_OK)
