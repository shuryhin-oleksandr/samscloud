import json
from difflib import SequenceMatcher
from io import BytesIO
import sys
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models import Q
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.conf import settings
from rest_framework import serializers
from string import ascii_letters
from random import choice, randint
from rest_framework.response import Response
from django_rest_passwordreset.serializers import EmailSerializer, PasswordTokenSerializer

from .utils import get_tokens_for_user, send_account_activation_email, send_twilio_sms, send_emergency_contact_mail, send_push_notification
import re
from rest_framework.serializers import (
    CharField,
    EmailField,
    HyperlinkedIdentityField,
    ModelSerializer,
    ValidationError,
    Serializer,
    ImageField,
)
from fcm_django.models import FCMDevice
from apps.organization.models import OrganizationProfile, EmergencyContact
from ...incident.models import Incident
from ...reports.models import NotificationSettings, CurrentUserLocation, NotificationHistory

User = get_user_model()

class UsersListSerializer(ModelSerializer):
    """
    User List Serializer
    """
    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'phone_number',
        ]
class UserCreateSerializer(ModelSerializer):
    """
    User Register serializer
    """
    email = EmailField(label='Email Address')
    password = CharField(write_only=True)
    confirm_password = CharField(write_only=True)
    fcm_token = CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'user_type',
            'address',
            'state',
            'country',
            'city',
            'zip',
            'password',
            'confirm_password',
            'phone_number',
            'fcm_token',
        ]

    def validate_email(self, value):
        email = value.lower().strip()

        user_qs = User.objects.filter(email=email)

        if user_qs.exists():
            raise ValidationError("This user has already registered.")

        return value

    def validate_phone_number(self, value):
        phone_number = value
        user_qs = User.objects.filter(phone_number=phone_number)
        if user_qs.exists():
            raise ValidationError("This phone has already registered.")
        return value

    def validate_password(self, value):
        data = self.get_initial()
        password1 = value
        password2 = data.get('confirm_password')
        if password1 != password2:
            raise ValidationError('Passwords Must Match')
        if not re.match(r"^(?=.*[\d])(?=.*[A-Z])(?=.*[a-z])(?=.*[~!@#$%^&*()_+\.])[\w\d~!@#$%^&*()_+\.]{6,}$", password1):
            raise ValidationError(
                'Your password has to be at least 6 characters long.'
                ' Must contain at least one lower case letter, '
                'one upper case letter, one digit. at least one special character'
                ' ~!@#$%^&*()_+.')
        return value

    def create(self, validated_data):
        first_name = validated_data.get('first_name', None)
        last_name = validated_data.get('last_name', None)
        email = validated_data.get('email', None)
        address = validated_data.get('address', None)
        state = validated_data.get('state', None)
        city = validated_data.get('city', None)
        country = validated_data.get('country', None)
        zip = validated_data.get('zip', None)
        phone_number = validated_data.get('phone_number', None)
        user_type = validated_data.get('user_type', None)
        user_obj = User(
            first_name=first_name,
            last_name=last_name,
            email=email.lower().strip(),
            address=address,
            state=state,
            city=city,
            country=country,
            zip=zip,
            user_type=user_type,
            phone_number=phone_number,
            is_active=False,
            is_verified=False,
        )
        user_obj.set_password(validated_data['password'])
        user_obj.save()
        user = User.objects.get(email=email.lower().strip())
        notification = NotificationSettings(user=user)
        notification.save()
        currentlocation = CurrentUserLocation(user=user)
        currentlocation.save()
        registration_id = validated_data.get('fcm_token', None)
        if registration_id:
            FCMDevice.objects.create(user=user_obj, type='ios', registration_id=registration_id)
        return validated_data


class UserActivationSerializer(Serializer):
    """
    Serializer for activate user account via clicking on mail link
    """
    uidb64 = CharField()
    token = CharField()
    pro_code = CharField(write_only=True)
    password = CharField(label='Password', write_only=True)
    confirm_password = CharField(label='Confirm Password', write_only=True)

    def validate_password(self, value):
        data = self.get_initial()
        password1 = value
        password2 = data.get('confirm_password')
        if password1 != password2:
            raise ValidationError('Passwords Must Match')
        if not re.match(r"^(?=.*[\d])(?=.*[A-Z])(?=.*[a-z])(?=.*[~!@#$%^&*()_+\.])[\w\d~!@#$%^&*()_+\.]{6,}$", password1):
            raise ValidationError(
                'Your password has to be at least 6 characters long.'
                ' Must contain at least one lower case letter, '
                'one upper case letter, one digit. at least one special character'
                ' ~!@#$%^&*()_+.')
        return value



class UserDetailUpdateSerializer(ModelSerializer):
    """
    User Retrieve Update Serializer
    """

    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'profile_logo',
            'email',
            'address',
            'state',
            'city',
            'zip',
            'user_type',
            'phone_number',
            'date_joined',
            'photo_location',
            'is_verified',
            'device_id',
            'lat',
            'long',
            'altitude',
            'speed',
            'location_time',
            'pending_status',
            'battery_power'
        ]




class UserLoginSerializer(ModelSerializer):
    """
    User Login Serializer
    """
    token = CharField(allow_blank=True, read_only=True)
    refresh_token = CharField(allow_blank=True, read_only=True)
    email = EmailField(label='Email Address')
    organization_id = CharField(allow_blank=True, read_only=True)
    fcm_token = CharField(write_only=True, required=False, allow_blank=True)
    verified_status = serializers.SerializerMethodField(read_only=True)
    profile_logo = serializers.SerializerMethodField(read_only=True)
    organization = CharField(required=False, write_only=True)
    organization_code = serializers.SerializerMethodField(read_only=False)
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'password',
            'token',
            'refresh_token',
            'organization_id',
            'fcm_token',
            'verified_status',
            'profile_logo',
            'organization_code',
            'organization'
        ]
        extra_kwargs = {"password": {"write_only": True},
                        }

    def to_representation(self, instance):
        data = super(UserLoginSerializer, self).to_representation(instance)
        user = User.objects.get(id=instance.get('id'))
        data.update({"state": user.state, "city": user.city, "zip": user.zip, "address": user.address, "first_name": user.first_name, "phone_number": user.phone_number, "last_name": user.last_name,})
        try:
            location = CurrentUserLocation.objects.get(user=user)
            notification = NotificationSettings.objects.get(user=user)
            data.update({"share_location": location.share_location, "new_message": notification.new_message, "contact_request": notification.contact_request, "contact_disable_location": notification.contact_disable_location,
                         "crisis_emergency_alert": notification.crisis_emergency_alert, "contact_has_incident": notification.contact_has_incident, "send_incident_text": notification.send_incident_text,
                         "send_incident_email": notification.send_incident_email, "app_tips": notification.app_tips, "new_updates": notification.new_updates, "bluetooth": notification.bluetooth,
                         "nfc": notification.nfc, "siri_incident_start": notification.siri_incident_start, "auto_route_incident_organization": notification.auto_route_incident_organization, "auto_route_contacts": notification.auto_route_contacts,
                         "shake_activate_incident": notification.shake_activate_incident})
        except:

            print("data")
        return data

    def get_verified_status(self, obj):
        user_obj = User.objects.get(id=obj.get('id'))
        if not (user_obj.is_active and (user_obj.is_verified or user_obj.is_phone_number_verified)):
            return False
        return True

    def get_profile_logo(self, obj):
        request = self.context.get("request", None)
        user_obj = User.objects.get(id=obj.get('id'))
        if user_obj.profile_logo:
            profile_logo = request.build_absolute_uri(user_obj.profile_logo.url)
            return profile_logo
        return None

    def get_organization_code(self, obj):
        ord_id = self.context.get('request').data.get("organization", None)
        org_obj = OrganizationProfile.objects.filter(id=ord_id)
        org_code = None
        if org_obj.exists():
            org_code = org_obj.first().pro_code
        return org_code

    def validate(self, data):
        user_obj = None
        email = data.get("email", None)
        password = data["password"]
        if not email or not password:
            raise ValidationError("Email and password required")
        email = email.lower().strip()
        user = User.objects.filter(email=email).distinct()
        if user.exists() and user.count() == 1:
            user_obj = user.first()
        else:
            raise ValidationError('There is no user registered with %s' % email)
        if user_obj:
            if user_obj.password == '':
                raise ValidationError('You have not verified your account. Please verify it before login')
            if not user_obj.check_password(password):
                raise ValidationError('Incorrect credentials. Please try again')

        org_id = data.get("organization", None)
        if org_id:
            org_obj = OrganizationProfile.objects.filter(id=org_id)
            if not org_obj:
                raise ValidationError('Invalid organization')

        try:
            org_obj = OrganizationProfile.objects.get(email=user_obj.email)
            data['organization_id'] = org_obj.id
        except:
            data['organization_id'] = None
        registration_id = data.get("fcm_token", None)
        if registration_id:
            fcm_obj, created = FCMDevice.objects.get_or_create(user=user_obj, type='ios')
            fcm_obj.registration_id = registration_id
            fcm_obj.save()
        response_token = get_tokens_for_user(user_obj)
        data['token'] = response_token.get('access', None)
        data['refresh_token'] = response_token.get('refresh', None)
        data['id'] = user_obj.id
        return data




user_detail_url = HyperlinkedIdentityField(
    view_name='accounts-api:detail',
    lookup_field='pk'
)


class UserListSerializer(ModelSerializer):
    """
    User list Serializer
    """
    url = user_detail_url

    class Meta:
        model = User
        fields = [
            'id',
            'url',
            'first_name',
            'last_name',
            'email',
            'address',
            'state',
            'city',
            'zip',
            'user_type',
            'phone_number',
        ]




class UserSerializer(ModelSerializer):
    """
    User Retrieve Update Serializer
    """

    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'profile_logo',
            'email',
            'address',
        ]

class UserEmailSerializer(Serializer):
    """
    The serializer that checks if the email does exist
    """
    email = EmailField(label='Email Address')

    def validate(self, data):
        email = data.get("email", None)
        user = User.objects.filter(email=email).distinct()
        if user.exists() and user.count() == 1:
            raise ValidationError('There is user already registered with %s' % email)
        return data


class UserEmailCheckSerializer(EmailSerializer):
    """
    The serializer that checks if the email does exist
    """

    def validate_email(self, email):
        if not User.objects.filter(email=email).exists():
            raise ValidationError('There is no user with this email registered with us')
        return email


class ResetPasswordSerializer(Serializer):
    """
    Serializer for Reset Password
    """
    new_password = CharField(write_only=True)
    confirm_password = CharField(write_only=True)

    def validate(self, data):
        new_password = data.get("new_password", None)
        confirm_password = data.get("confirm_password", None)
        user = self.context.get('user')
        if new_password != confirm_password:
            raise ValidationError('Passwords Must Match')

        if not re.match(r"^(?=.*[\d])(?=.*[A-Z])(?=.*[a-z])(?=.*[~!@#$%^&*()_+\.])[\w\d~!@#$%^&*()_+\.]{6,}$",
                        new_password):
            raise ValidationError(
                'Your password has to be at least 6 characters long.'
                ' Must contain at least one lower case letter, '
                'one upper case letter, one digit. at least one special character'
                ' ~!@#$%^&*()_+.')
        user.set_password(new_password)
        user.save()
        return data


class MobileNumberSerializer(Serializer):
    """
    Serializer to send SMS OTP
    """
    email = EmailField(label='Email Address')
    mobile_number = CharField(label='Mobile Number')

    def validate(self, data):
        email = data.get("email", None)
        mobile_number = data.get("mobile_number", None)
        if not email:
            raise ValidationError('email can not be null')
        if not mobile_number:
            raise ValidationError('Mobile number can not be null')
        if User.objects.filter(phone_number=mobile_number).exists():
            if not User.objects.filter(email=email, phone_number=mobile_number).exists():
                raise ValidationError('This mobile number has already registered')

        return data


class MobileOTPSerializer(Serializer):
    """
    Serializer to verify SMS OTP
    """
    email = EmailField(label='Email Address')
    otp = CharField(label='Enter OTP')

    def validate(self, data):
        otp = data.get("otp", None)
        if not otp:
            raise ValidationError('Please enter the OTP')
        if len(otp) != 4:
            raise ValidationError('The OTP Should be 4 digits')
        return data


class ProfilePicSerializer(Serializer):
    """
    Serializer to post profile picture
    """
    email = EmailField(label='Email Address')
    profile_logo = ImageField(label="Profile Picture", write_only=True)
    profile_logo_url = CharField(read_only=True)

    def validate(self, data):
        email = data.get("email", None)
        profile_logo = data.get("profile_logo", None)
        if not email:
            raise ValidationError("Please provide email address")
        if not profile_logo:
            raise ValidationError("Please upload Image")
        if not User.objects.filter(email=email).exists():
            raise ValidationError("No user exist with email %s" % email)
        user_obj = User.objects.get(email=email)
        foo = Image.open(profile_logo)
        foo = foo.convert('RGB')
        foo = foo.resize((160, 300), Image.ANTIALIAS)
        profile_logo_io = BytesIO()
        foo.save(profile_logo_io, format='JPEG', quality=95)
        # foo.save(profile_logo, quality=95)
        reszied_profile_logo = InMemoryUploadedFile(profile_logo_io, 'ImageField', profile_logo.name, 'image/jpeg',
                                                    sys.getsizeof(profile_logo_io), None)
        user_obj.profile_logo = reszied_profile_logo
        user_obj.save()
        data['profile_logo_url'] = user_obj.profile_logo.url
        return data


class CustomPasswordTokenSerializer(PasswordTokenSerializer):
    """
    Serializer to verify forgot password
    """
    confirm_password = CharField(label="Password", style={'input_type': 'password'})

    def validate_password(self, value):
        data = self.get_initial()
        password1 = value
        password2 = data.get('confirm_password')
        if password1 != password2:
            raise ValidationError('Passwords must match')
        if not re.match(r"^(?=.*[\d])(?=.*[A-Z])(?=.*[a-z])(?=.*[~!@#$%^&*()_+\.])[\w\d~!@#$%^&*()_+\.]{6,}$", password1):
            raise ValidationError(
                'Your password has to be at least 6 characters long.'
                ' Must contain at least one lower case letter, '
                'one upper case letter, one digit. at least one special character'
                ' ~!@#$%^&*()_+.')
        return value


class UserResetPasswordSerializer(Serializer):
    """
    Serializer for profile page password reset
    """
    current_password = CharField(write_only=True)
    new_password = CharField(write_only=True)
    confirm_password = CharField(write_only=True)

    def validate(self, data):
        current_password = data.get("current_password", None)
        new_password = data.get("new_password", None)
        confirm_password = data.get("confirm_password", None)
        user = self.context.get('user')
        if not user.check_password(current_password):
            raise ValidationError("Current password does not match")
        if new_password != confirm_password:
            raise ValidationError('Passwords Must Match')
        if current_password == new_password:
            raise ValidationError('old password and new password are the same!')

        if not re.match(r"^(?=.*[\d])(?=.*[A-Z])(?=.*[a-z])(?=.*[~!@#$%^&*()_+\.])[\w\d~!@#$%^&*()_+\.]{6,}$",
                        new_password):
            raise ValidationError(
                'Your password has to be at least 6 characters long.'
                ' Must contain at least one lower case letter, '
                'one upper case letter, one digit. at least one special character'
                ' ~!@#$%^&*()_+.')
        user.set_password(new_password)
        user.save()
        return data


class MobileForgotPasswordSerializer(Serializer):
    """
    Serializer for Mobile forgot password
    """
    email = CharField(label="Enter email Address")
    otp = CharField(label="Enter OTP", allow_blank=True, allow_null=True, required=False)

    def validate(self, data):
        email = data.get("email", None)
        qs = User.objects.filter(email=email)
        if not qs.exists():
            raise ValidationError("The user with %s not found" % (email))
        user_obj = qs.first()
        if not user_obj.phone_number:
            raise ValidationError("There is no mobile number associated with this user")
        return data


class MobileResetPasswordSerializer(ResetPasswordSerializer):
    """
    Serializer for IOS reset password.
    """
    email = CharField(label="Enter email address")


class FCMDeviceSerializer(ModelSerializer):
    """
    Serializer to create FCM tokens
    """

    class Meta:
        model = FCMDevice
        exclude = ('user', 'type')

    def create(self, validated_data):
        name = validated_data.get("name", None)
        registration_id = validated_data.get("registration_id", None)
        device_id = validated_data.get("device_id", None)
        request = self.context.get("request", None)
        fcm_obj, created = FCMDevice.objects.get_or_create(user=request.user, type='ios')
        fcm_obj.name = name
        fcm_obj.registration_id = registration_id
        fcm_obj.device_id = device_id
        fcm_obj.save()
        return validated_data


class EmergencyContactRequestCheckinSerializer(Serializer):
    contact_id = CharField(required=True)

    def validate(self, attrs):
        request = self.context.get('request', None)
        current_usr = request.user
        user_obj = None
        try:
            contact_id =attrs['contact_id']
            contact_obj = EmergencyContact.objects.filter(id=contact_id)
            if not contact_obj:
                raise serializers.ValidationError('No user found with this contact ID')
            if contact_obj[0].email is not None:
                user_obj = User.objects.filter(email=contact_obj[0].email)
            elif contact_obj[0].phone_number is not None:
                user_obj = User.objects.filter(phone_number=contact_obj[0].phone_number)
            if not user_obj:
                raise serializers.ValidationError('User is not an app user')
        except EmergencyContact.DoesNotExist:
                pass
        return attrs


class ContactLocationUpdateerializer(Serializer):
    contact_id = CharField(required=True)
    checkin_status = CharField(required=True)
    latitude = CharField(required=False)
    longitude = CharField(required=False)
    address = CharField(required=False)

    def validate(self, attrs):
        user_obj = None
        try:
            contact_id = attrs['contact_id']
            checkin_status = attrs['checkin_status']
            contact_obj = EmergencyContact.objects.filter(id=contact_id)
            if not contact_obj:
                raise serializers.ValidationError('No user found with this contact ID')
            if checkin_status == 'Accepted':
                if not 'latitude' in attrs or not 'longitude' in attrs or not 'address' in attrs:
                    raise serializers.ValidationError('please share the location details')
                if attrs['latitude'] is None or attrs['longitude'] is None or attrs['address'] is None:
                    raise serializers.ValidationError('please share the location details')
        except EmergencyContact.DoesNotExist:
            pass
        return attrs



class EmergencyContactAddSerializer(ModelSerializer):
    """
    Serializer to add Emergency contact
    """
    user = UserDetailUpdateSerializer(read_only=True)

    class Meta:
        model = EmergencyContact
        exclude = ('status', 'request_checkin_updated', 'request_checkin_latitude', 'request_checkin_longitude', 'request_checkin_address',)

    def validate(self, attrs):
        try:
            user = self.context['request'].user
            if 'phone_number' in attrs:
                if attrs['phone_number'] == '':
                    attrs.pop('phone_number')

            if 'email' in attrs:
                if attrs['email'] == '':
                    attrs.pop('email')

            if 'phone_number' in attrs:
                contact_qs = EmergencyContact.objects.filter(user=user, phone_number=attrs['phone_number'])
                if contact_qs.exists():
                    raise serializers.ValidationError('Emergency contact with this phone number already exists')
                # else:
                #     return attrs
            if 'email' in attrs:
                if user.email == attrs['email']:
                    raise serializers.ValidationError("You have added your own contact details, Please add "
                                                      "another contact")
                contact_qs = EmergencyContact.objects.filter(user=user, email=attrs['email'])
                if contact_qs.exists():
                    raise serializers.ValidationError('Emergency contact with this email ID already exists')
                # else:
                #     return attrs
            if 'phone_number' not in attrs and 'email' not in attrs:
            # else:
                raise serializers.ValidationError('Please provide phone number or email ID')
            else:
                return attrs
        except EmergencyContact.DoesNotExist:
            pass
        return attrs

    def create(self, validated_data):
        email = validated_data.get('email', None)
        name = validated_data.get('name', None)
        phone_number = validated_data.get('phone_number', None)
        relationship = validated_data.get('relationship', None)
        contact_type = validated_data.get('contact_type', None)
        request = self.context.get('request', None)
        current_usr = request.user

        emergency_contact_obj = EmergencyContact.objects.create(user=current_usr,
                                                                email=email,
                                                                name=name,
                                                                relationship=relationship, phone_number=phone_number,
                                                                contact_type=contact_type)


        activate_url = "{0}://{1}/emergency-contact/activate?uid={2}".format(request.scheme,
                                                                             settings.FRONTEND_DOMAIN,
                                                                             emergency_contact_obj.uuid)
        print(activate_url)

        if email is not None:
            qs = FCMDevice.objects.filter(Q(user__email=email) | Q(user__phone_number=phone_number))
            if qs.exists():
                user_bj = User.objects.filter(
                    Q(email=emergency_contact_obj.email) | Q(
                        phone_number=emergency_contact_obj.phone_number)).first()
                setting = NotificationSettings.objects.get(user=user_bj)
                if setting.contact_request == True:
                    fcm_obj = qs.first()
                    data = {
                        "type": "accept_contact",
                        "token": str(emergency_contact_obj.uuid),
                    }
                    message = "%s has added you as an %s contact. Please accept or reject" % (current_usr.first_name, contact_type)
                    title = "You are added as %s contact" % (contact_type)
                    send_push_notification.delay(fcm_obj.id, title, message, data)
                    histroy = NotificationHistory(user=user_bj, requested_user=current_usr, attribute=data, requested_token=str(emergency_contact_obj.uuid), notification_type="accept_contact", message=message,
                                        title=title)
                    histroy.save()
            send_emergency_contact_mail(request, emergency_contact_obj.uuid, name, email, contact_type)
        if phone_number:
            message = "This is to inform you that, your Contact has been added to %s's  %s contact list.Please click this link to confirm the request %s" % (
                current_usr.first_name, contact_type, activate_url)
            to = phone_number
            send_twilio_sms.delay(message, to)
        return emergency_contact_obj


class EmergencyContactActivateSerializer(Serializer):
    """
    Serializer to activate the Emergency contact
    """
    uuid = CharField(label="Enter UUID")
    status = CharField(label='Status')
    latitude = CharField(label="Latitude", allow_blank=True, allow_null=True, required=False)
    longitude = CharField(label="longitude", allow_blank=True, allow_null=True, required=False)

    def validate(self, data):
        contact_obj = EmergencyContact.objects.filter(uuid=data.get('uuid'))
        if not contact_obj:
            raise serializers.ValidationError('There is no emergency contact with this ID')
        else:
            return data


class EmergencyContactDeleteSerializer(ModelSerializer):
    """
    Serializer to delete an emergency contact
    """

    class Meta:
        model = EmergencyContact
        exclude = ()


class EmergencyContactDetailsSerializer(ModelSerializer):
    """
    Serializer to list emergency contact details
    """
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    request_sent_date = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()

    class Meta:
        model = EmergencyContact
        exclude = ('request_checkin_updated', 'request_checkin_latitude', 'request_checkin_longitude', 'request_checkin_address',)

    def get_created_at(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')

    def get_updated_at(self, obj):
        return obj.updated_at.strftime('%Y-%m-%d %H:%M:%S')

    def get_request_sent_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')

    def get_address(self, obj):
        address = None
        address_qs = None
        try:
            if obj.email:
                address_qs = User.objects.filter(email=obj.email)
            elif obj.phone_number:
                address_qs = User.objects.filter(phone_number=obj.phone_number)
            if address_qs:
                address = address_qs[0].address
        except:
            address = None
        return address


    def get_profile_image(self, obj):
        profile_image = None
        profile_image_qs = None
        request = self.context.get("request", None)
        try:
            if obj.email:
                profile_image_qs = User.objects.filter(email=obj.email)
            elif obj.phone_number:
                profile_image_qs = User.objects.filter(phone_number=obj.phone_number)
            if profile_image_qs:
                profile_image = request.build_absolute_uri(profile_image_qs[0].profile_logo.url)
        except:
            profile_image = None
        return profile_image

    def to_representation(self, instance):
        data = super(EmergencyContactDetailsSerializer, self).to_representation(instance)
        try:
            data_obj = {}
            user = User.objects.get(email=instance.email)
            location = CurrentUserLocation.objects.get(user=user)
            data_obj.update({"location_share_location": location.share_location, "location_address": location.address, "location_latitude": location.latitude,
                             "location_longitude": location.longitude, "location_last_updated": location.updated_at})
            data.update({"location_status": data_obj})
        except:
            data.update({"location_status": {}})

        try:
            checkin_data_obj = {}
            checkin_data_obj.update({"request_checkin_address": instance.request_checkin_address, "request_checkin_latitude": instance.request_checkin_latitude,
                             "request_checkin_longitude": instance.request_checkin_longitude, "request_checkin_last_updated": instance.request_checkin_updated})
            data.update({"request_checkin_data": checkin_data_obj})
        except:
            data.update({"request_checkin_data": {}})
        return data


class UserProfileSerializer(ModelSerializer):
    """
    User profile detail serializer
    """


    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'state',
            'city',
            'address',
            'zip',
        ]
        read_only_fields = ("id", )

class UserDetailsSerializer(ModelSerializer):
    """
    User Retrieve Update Serializer
    """

    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'profile_logo',
            'email',
            'address',
            'state',
            'city',
            'zip',
            'phone_number'
        ]

    def to_representation(self, instance):
        data = super(UserDetailsSerializer, self).to_representation(instance)
        user = User.objects.get(id=instance.id)
        data.update({"Emergency-contact-count": EmergencyContact.objects.filter(user=user, contact_type="Emergency", status="Accepted").count(), "Family-contact-count": EmergencyContact.objects.filter(user=user, contact_type="Family", status="Accepted").count(),
                     "ongoing-incident-count": Incident.objects.filter(user=user, is_ended=False, is_stopped=False, is_started=True).count(), "history-incident-count": Incident.objects.filter(Q(user=user, is_ended=True) | Q(user=user, is_stopped=True)).count()})
        return data

class UserNotificationSerializer(ModelSerializer):
    """
    User Retrieve Update Serializer
    """

    class Meta:
        model = NotificationSettings
        fields = [
            'new_message',
            'contact_request',
            'contact_disable_location',
            'crisis_emergency_alert',
            'contact_has_incident',
            'send_incident_text',
            'send_incident_email',
            'app_tips',
            'new_updates',
            'id',
        ]
        read_only_fields = ("id", "user ",)

class UserCurrentLocationSerializer(ModelSerializer):
    """
    User Retrieve Update Serializer
    """

    class Meta:
        model = CurrentUserLocation
        fields = [
            'share_location',
            'address',
            'latitude',
            'longitude',
            'id',
        ]
        read_only_fields = ("id", "user ", "share_location",)

class ShareLocationSerializer(ModelSerializer):
    """
    User Retrieve Update Serializer
    """

    class Meta:
        model = CurrentUserLocation
        fields = [
            'share_location',
            'address',
            'latitude',
            'longitude',
            'id',
        ]
        read_only_fields = ("id", "user ", "longitude", "address", "latitude",)

class UserSettingsSerializer(ModelSerializer):
    """
    User Retrieve Update Serializer
    """

    class Meta:
        model = NotificationSettings
        fields = [
            'bluetooth',
            'nfc',
            'siri_incident_start',
            'auto_route_incident_organization',
            'auto_route_contacts',
            'shake_activate_incident',
            'id',
        ]
        read_only_fields = ("id", "user ",)

class NotificationHistorySerializer(ModelSerializer):
    """
    User Retrieve Update Serializer
    """

    class Meta:
        model = NotificationHistory
        fields = [
            'user',
            'notification_type',
            'message',
            'title',
            'is_read',
            'date_created',
            'id',
        ]

    def to_representation(self, instance):
        data = super(NotificationHistorySerializer, self).to_representation(instance)
        if instance.notification_type == "incident_ended":
            d = UserDetailUpdateSerializer(instance.requested_user)
            data.update({"user-ended-incident": d.data})
            if instance.attribute != None:
                data.update({"ended-incident-details": instance.attribute})
        elif instance.notification_type == "responder_alert":
            d = UserDetailUpdateSerializer(instance.requested_user)
            data.update({"user-ended-incident": d.data, "contact-uuid": instance.requested_token})
            if instance.attribute != None:
                data.update({"start-incident-details": instance.attribute})
        elif instance.notification_type == "request-check-in":
            d = UserDetailUpdateSerializer(instance.requested_user)
            data.update({"user-request-checkin": d.data})
            if instance.attribute != None:
                data.update({"emergency-contact-details": instance.attribute})
        elif instance.notification_type == "contact-location-update":
            d = UserDetailUpdateSerializer(instance.requested_user)
            data.update({"location-updated-user": d.data})
        elif instance.notification_type == "accept_contact":
            d = UserDetailUpdateSerializer(instance.requested_user)
            data.update({"contact-requested-user": d.data, "contact-uuid": instance.requested_token})
            if instance.attribute != None:
                data.update({"emergency-contact-details": instance.attribute})
        elif instance.notification_type == "emergency_contact_response":
            if instance.requested_user:
                d = UserDetailUpdateSerializer(instance.requested_user)
                data.update({"contact-requested-user": d.data})
            else:
                contact_obj = EmergencyContact.objects.filter(uuid=instance.attribute['uuid']).first()
                if contact_obj:
                    newdata = EmergencyContactDetailsSerializer(contact_obj).data
                    data.update({"contact-requested-user": newdata})
            if instance.attribute != None:
                data.update({"emergency-contact-details": instance.attribute})
        elif instance.notification_type == "share-loaction":
            d = UserDetailUpdateSerializer(instance.requested_user)
            data.update({"share-loaction-user": d.data})
        elif instance.notification_type == "organization-message":
            d = UserDetailUpdateSerializer(instance.requested_user)
            data.update({"organization-messaged-user": d.data})
            if instance.attribute != None:
                data.update({"organization-message-details": instance.attribute})
        elif instance.notification_type == "geofence-request-check-in":
            d = UserDetailUpdateSerializer(instance.requested_user)
            data.update({"geofence-requested-user": d.data})
            if instance.attribute != None:
                data.update({"geofence-checkin-details": instance.attribute})
        elif instance.notification_type == "geofence_contact_response":
            d = UserDetailUpdateSerializer(instance.requested_user)
            data.update({"geofence-user": d.data})
            if instance.attribute != None:
                data.update({"geofence-details": instance.attribute})
        elif instance.notification_type == "geofence_stop_sharing":
            d = UserDetailUpdateSerializer(instance.requested_user)
            data.update({"geofence-user": d.data})
            if instance.attribute != None:
                data.update({"geofence-details": instance.attribute})
        elif instance.notification_type == "geofence_alert":
            d = UserDetailUpdateSerializer(instance.requested_user)
            data.update({"geofence-user": d.data})
            if instance.attribute != None:
                data.update({"geofence-details": json.loads(instance.attribute)})
        elif instance.notification_type == "geofence-hide_checkin":
            d = UserDetailUpdateSerializer(instance.requested_user)
            data.update({"geofence-user": d.data})
            if instance.attribute != None:
                data.update({"geofence-details": json.loads(instance.attribute)})
        elif instance.notification_type == "left_geofence":
            d = UserDetailUpdateSerializer(instance.requested_user)
            data.update({"geofence-user": d.data})
            if instance.attribute != None:
                data.update({"geofence-details": json.loads(instance.attribute)})
        elif instance.notification_type == "hide_checkin_geofence":
            d = UserDetailUpdateSerializer(instance.requested_user)
            data.update({"geofence-user": d.data})
            if instance.attribute != None:
                data.update({"geofence-details": json.loads(instance.attribute)})
        elif instance.notification_type == "responder_joined":
            d = UserDetailUpdateSerializer(instance.requested_user)
            data.update({"joinedresponder-user": d.data})
            if instance.attribute != None:
                data.update({"reponder-details": instance.attribute})
        return data