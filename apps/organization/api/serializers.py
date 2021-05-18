from django.conf import settings
import re
import requests
import json
from ..models import OrganizationProfile, UserOrganization, OrganizationContact, EmergencyContact, OrganizationType, \
    OrganizationAddress, OrganizationFloors, OrganizationGeoFence, ZoneCCTV, ZoneDocument, Zone, ZoneFloor, \
    OrganizationMessage
from django.contrib.auth import get_user_model
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from string import ascii_letters
from random import choice, randint

from apps.accounts.api.serializers import UserListSerializer, UserDetailUpdateSerializer
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from apps.accounts.api.utils import send_organization_activation_email, send_organization_welcome_mail, \
    send_emergency_contact_mail, send_twilio_sms

import base64
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.response import Response

from django.core.files.base import ContentFile
from fcm_django.models import FCMDevice
from rest_framework.serializers import (
    CharField,
    EmailField,
    ModelSerializer,
    ValidationError,
    Serializer,
    SerializerMethodField,
    FileField,
    BooleanField
)

User = get_user_model()


class OrganizationContactAddSerializer(ModelSerializer):
    """
    Serializer to add organization contact
    """

    class Meta:
        model = OrganizationContact
        exclude = ['user']

    def create(self, validated_data):
        email = validated_data.get('email', None)
        name = validated_data.get('name', None)
        role = validated_data.get('contact_role', None)
        organization = validated_data.get('organization', None)
        phone_number = validated_data.get('phone_number', None)
        request = self.context.get('request', None)
        current_usr = request.user
        try:
            organization = OrganizationProfile.objects.get(id=organization)
        except:
            raise ValidationError('Organization not found')
        contact_obj_email = OrganizationContact.objects.filter(organization=organization, email=email)
        contact_obj_phno = OrganizationContact.objects.filter(organization=organization, phone_number=phone_number)
        if contact_obj_email:
            contact_obj = contact_obj_email.update(organization=organization, user=current_usr,
                                                               email=email,
                                                               name=name,
                                                               contact_role=role, phone_number=phone_number)
        elif contact_obj_phno:
            contact_obj= contact_obj_phno.update(organization=organization, user=current_usr,
                                                               email=email,
                                                               name=name,
                                                               contact_role=role, phone_number=phone_number)
        else:
            contact_obj = OrganizationContact.objects.create(organization=organization, user=current_usr,
                                                                       email=email,
                                                                       name=name,
                                                                       contact_role=role, phone_number=phone_number)
        if User.objects.filter(email=email).exists():
            user_obj = User.objects.get(email=email)
        else:
            user_obj = User.objects.create(email=email, first_name=name, user_type='Responder')
        if not user_obj.is_verified:
            send_organization_activation_email(request, user_obj, organization)
        else:
            if not UserOrganization.objects.filter(user=user_obj, organization=organization).exists():
                send_organization_welcome_mail(request, user_obj, organization)
                UserOrganization.objects.create(user=user_obj, organization=organization)
        return contact_obj


class OrganizationContactListSerializer(ModelSerializer):
    """
    Serializer to List organization contacts
    """
    organization = SerializerMethodField()

    class Meta:
        model = OrganizationContact
        fields = '__all__'

    def get_organization(self, obj):
        try:
            return {'name': obj.organization.organization_name, 'id': obj.organization.id}
        except:
            return {'name': None, 'id': None}


class ParentOrganizationProfileSerializer(ModelSerializer):
    """
    Serializer to add organization profile
    """
    pro_code = CharField(label='Pro Code', read_only=True)
    contacts = OrganizationContactAddSerializer(many=True, read_only=True)

    class Meta:
        model = OrganizationProfile
        fields = [
            'id',
            'parent_organization',
            'contacts',
            'organization_name',
            'contact_name',
            'logo',
            'phone_number',
            'description',
            'organization_email',
            'organization_type',
            'is_dispatch',
            'is_alert_sams',
            'url',
            'who_can_join',
            'role',
            'email',
            'latitude',
            'longitude',
            'pro_code',
            'address',
            'number_of_floors'
        ]

    def validate(self, data):
        email = data.get('email', None)
        if OrganizationProfile.objects.filter(email=email).exists():
            raise ValidationError("This mail is registered in another organization as owner")
        return data


class  OrganizationListForLoginSerializer(ModelSerializer):
    """
    Serializer to list organization details
    """

    class Meta:
        model = OrganizationProfile
        fields = [
            'id',
            'organization_name']


class OrganizationTypeSerializer(ModelSerializer):
    """
    Serializer to list organization type
    """

    class Meta:
        model = OrganizationType
        fields = [
            'id',
            'type_name',
        ]


class OrganizationListSerializer(ModelSerializer):
    """
    Serializer to list organization details
    """
    organization_type = OrganizationTypeSerializer(read_only=True)
    dispatch = SerializerMethodField(read_only=True)
    alert = SerializerMethodField(read_only=True)
    
    class Meta:
        model = OrganizationProfile
        fields = [
            'id',
            'organization_name',
            'contact_name',
            'pro_code',
            'logo',
            'address',
            'who_can_join',
            'latitude',
            'longitude',
            'number_of_floors',
            'organization_type',
            'dispatch',
            'alert',
            'phone_number',
            'email',
            'is_covid_active'
        ]


    def get_dispatch(self, obj):
        request = self.context.get("request", None)
        try:
            if obj.is_dispatch == 1:
                dispatch = True
            else:
                dispatch = False
        except:
            dispatch = None
        return dispatch

    def get_alert(self, obj):
        request = self.context.get("request", None)
        try:
            if obj.is_alert_sams == 1:
                alert = True
            else:
                alert = False
        except:
            alert = None
        return alert

class UserOrganizationListSerializer(ModelSerializer):
    """
    Serializer to list user organization details
    """
    organization = OrganizationListSerializer(read_only=True)
    is_show_covid_info = BooleanField(required=True)

    class Meta:
        model = UserOrganization
        fields = [
            'organization',
            'is_show_covid_info'
        ]


class OrganizationUpdateSerializer(ModelSerializer):
    """
    Serializer to update the organization profile
    """
    contacts = OrganizationContactAddSerializer(many=True, read_only=True)
    logo_url = SerializerMethodField(read_only=True)

    class Meta:
        model = OrganizationProfile
        fields = [
            'parent_organization',
            'organization_name',
            'contacts',
            'contact_name',
            'role',
            'email',
            'latitude',
            'longitude',
            'logo',
            'phone_number',
            'pro_code',
            'organization_type',
            'is_dispatch',
            'is_alert_sams',
            'is_covid_active',
            'who_can_join',
            'url',
            'organization_email',
            'address',
            'is_email_verified',
            'is_alert_sams',
            'description',
            'logo_url',
            'number_of_floors',
            'shinobi_authkey',
            'shinobi_group_key'

        ]

    def get_logo_url(self, obj):
        request = self.context.get("request", None)
        try:
            logo = obj.logo.url
            logo = request.build_absolute_uri(logo)
        except:
            logo = None
        return logo

    def validate(self, data):
        organization_email = data.get("organization_email", None)
        if organization_email:
            organization_id = self.context.get('organization_id', None)
            if OrganizationProfile.objects.filter(organization_email=organization_email).exclude(
                    id=organization_id).exists():
                raise ValidationError('Organization email already used')

        return data


class ParentOrganizationDetailSerializer(ModelSerializer):
    """
    Serializer to list parent organization details
    """

    class Meta:
        model = OrganizationProfile
        fields = [
            'id',
            'organization_name',
            'contact_name',
            'role',
            'email',
            'logo',
            'phone_number',
            'pro_code',
            'organization_type',
            'is_dispatch',
            'is_alert_sams',
            'url',
            'organization_email',
        ]


class OrganizationDetailSerializer(ModelSerializer):
    """
    Serializer to list organization details
    """
    parent_organization_details = ParentOrganizationDetailSerializer(source='parent_organization')
    owner_id = SerializerMethodField(read_only=True)

    class Meta:
        model = OrganizationProfile
        fields = [
            'parent_organization_details',
            'id',
            'organization_name',
            'contact_name',
            'role',
            'email',
            'latitude',
            'longitude',
            'logo',
            'phone_number',
            'pro_code',
            'organization_type',
            'is_dispatch',
            'is_alert_sams',
            'is_covid_active',
            'url',
            'organization_email',
            'address',
            'description',
            'who_can_join',
            'is_dispatch',
            'is_alert_sams',
            'is_email_verified',
            'number_of_floors',
            'owner_id',
            'shinobi_authkey',
            'shinobi_group_key'
        ]

    def get_owner_id(self, obj):
        try:
            user_org_obj = UserOrganization.objects.get(organization=obj, user__email=obj.email).user
            user_obj = User.objects.get(id=user_org_obj.id, is_verified=True).id
        except:
            user_obj = None
        return user_obj


class GetOrganizationByProCodeSerializer(Serializer):
    """
    Serializer to get organization details by procode
    """
    pro_code = CharField(write_only=True)
    organization_name = CharField(label='Organization Name', read_only=True)
    organization_id = CharField(label='Organization Id', read_only=True)
    who_can_join = CharField(label='Who can Join', read_only=True)

    def validate(self, data):
        pro_code = data.get("pro_code", None)
        if not pro_code:
            raise ValidationError('Pro code cannot be empty')
        qs = OrganizationProfile.objects.filter(pro_code=pro_code)
        if not qs.exists():
            raise ValidationError('There is no organization related this Pro Code')
        organization_obj = qs.first()
        data['organization_name'] = organization_obj.organization_name
        data['organization_id'] = organization_obj.id
        data['who_can_join'] = organization_obj.who_can_join
        return data


class CheckProCodeSerializer(Serializer):
    """
    Serializer to check the procode in Organization profile
    """
    pro_code = CharField(label='Pro Code')
    already_exits = CharField(label='Is Pro Code already exists?', read_only=True)

    def validate(self, data):
        pro_code = data.get("pro_code", None)
        if not pro_code:
            raise ValidationError('Pro code cannot be empty')
        if OrganizationProfile.objects.filter(pro_code=pro_code).exists():
            data['already_exits'] = True
        else:
            data['already_exits'] = False
        return data





class OrganizationContactDetailUpdateDeleteSerializer(ModelSerializer):
    """
     Serializer to list organization contact details
    """

    class Meta:
        model = OrganizationContact
        fields = [
            'organization',
            'name',
            'contact_role',
            'phone_number',
            'email',
        ]


class OrganizationAddAddressSerializer(ModelSerializer):
    """
    Add organization address serializer
    """

    class Meta:
        model = OrganizationAddress
        fields = '__all__'

    def create(self, validated_data):
        organization = validated_data.get('organization', None)
        request = self.context.get('request', None)
        current_usr = request.user

        # Make sure the user associated with the organization
        if UserOrganization.objects.filter(user=current_usr, organization=organization).exists():
            organization_address = OrganizationAddress.objects.create(**validated_data)
            return organization_address
        else:
            raise PermissionDenied("You can't add address on this organization")


class OrganizationAddressListSerializer(ModelSerializer):
    class Meta:
        model = OrganizationAddress
        fields = '__all__'


class OrganizationFloorsSerializer(ModelSerializer):
    class Meta:
        model = OrganizationFloors
        fields = '__all__'

    def validate(self, data):
        altitude = data.get('altitude', None)
        if altitude:
            altitude_rgx = re.match(r'[a-zA-Z0-9,. ]+$', altitude)
            if not altitude_rgx:
                raise ValidationError("Altitude contains spacial characters")
        return data


class UserOrganizationCreateSerializer(ModelSerializer):
    class Meta:
        model = UserOrganization
        fields = ['id', 'organization']

    def validate(self, data):
        organization = data.get('organization')
        request = self.context.get("request")
        if UserOrganization.objects.filter(user=request.user, organization=organization).exists():
            raise ValidationError("Organization already added with the user")
        return data


class OrganizationEmailActivationSerializer(Serializer):
    uid = CharField(label="Enter the token")


class OrganizationGeoFenceSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = OrganizationGeoFence
        geo_field = 'co_ordinates'
        fields = '__all__'


class ZoneCCTVDeleteSerializer(Serializer):
    monitor_id = CharField(required=True)

    def validate(self, data):
        monitor_id = data.get("monitor_id", None)
        cctv_obj = ZoneCCTV.objects.filter(monitor_id=monitor_id)
        if not cctv_obj:
            raise ValidationError("Invalid Monitor ID %s" % monitor_id)
        else:
            return data


class DeleteZoneCCTVSerializer(Serializer):
    cctv_id = CharField(required=True)

    def validate(self, data):
        cctv_id = data.het


class ZoneSerializer(GeoFeatureModelSerializer):
    """
    Serializer for Organization Zones
    """

    class Meta:
        model = Zone
        geo_field = 'center_point'

        fields = [
            'id',
            'name',
            'organization',
            'center_point',
            'point1',
            'point2',
            'point3',
            'point4'
        ]


class ZoneCCTVSerializer(ModelSerializer):

    class Meta:
        model = ZoneCCTV
        fields = '__all__'


class ZoneCCTVGetSerializer(ModelSerializer):
    zone = SerializerMethodField()
    floor = SerializerMethodField()

    class Meta:
        model = ZoneCCTV
        fields = '__all__'

    def get_zone(self, obj):
        if obj.zone:
            zone_id = obj.zone.id
            name = obj.zone.name
            return {'id': zone_id, 'name': name}
        return None

    def get_floor(self, obj):
        if obj.floor:
            floor_id = obj.floor.id
            floor_number = obj.floor.floor_number
            return {'id': floor_id, 'floor_number': floor_number}
        return None


class ZoneDocumentSerializer(ModelSerializer):
    document = CharField(allow_null=True, allow_blank=True, required=False)
    url = SerializerMethodField(read_only=True)

    class Meta:
        model = ZoneDocument
        fields = '__all__'

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        file = validated_data.get('document', instance.document)
        if isinstance(file, str):
            format, filestr = file.split(';base64,')
            ext = format.split('/')[-1]
            file = ContentFile(base64.b64decode(filestr), name=instance.name + "." + ext)
        instance.document = file
        instance.save()
        return instance

    def get_url(self, obj):
        request = self.context.get("request", None)
        try:
            document_url = obj.document.url
            document_url = request.build_absolute_uri(document_url)
        except:
            document_url = None
        return document_url


class ZoneFloorSerializer(ModelSerializer):
    """
    Zone floor serializer to add CCTV and documentation
    """
    cctv_camera = ZoneCCTVSerializer(many=True, allow_null=True, required=False)
    document = ZoneDocumentSerializer(many=True, allow_null=True, required=False)

    class Meta:
        model = ZoneFloor
        fields = '__all__'

    def create(self, validated_data):
        cctv_data = validated_data.pop('cctv_camera', None)
        document_data = validated_data.pop('document', None)
        organization_zone = validated_data.get("organization_zone", None)
        floor = validated_data.get("floor", None)
        if ZoneFloor.objects.filter(organization_zone=organization_zone, floor=floor).exists():
            raise ValidationError("This floor already added to this zone")
        zone_floor = ZoneFloor.objects.create(**validated_data)
        if cctv_data:
            for cctv in cctv_data:
                cctv_obj = ZoneCCTV.objects.create(name=cctv['name'])
                zone_floor.cctv_camera.add(cctv_obj)
        if document_data:
            for document in document_data:
                try:
                    file_str = document['document']
                except:
                    file_str = None
                if file_str:
                    try:
                        format, filestr = file_str.split(';base64,')
                        ext = format.split('/')[-1]
                        file_obj = ContentFile(base64.b64decode(filestr), name=document['name'] + "." + ext)
                    except:
                        raise ValidationError('unsupported file type, it should be Base64 format')
                else:
                    file_obj = None
                document_obj = ZoneDocument.objects.create(name=document['name'], document=file_obj)
                zone_floor.document.add(document_obj)
        return zone_floor

    def update(self, instance, validated_data):
        cctv_data = validated_data.pop('cctv_camera', None)
        document_data = validated_data.pop('document', None)
        instance.floor = validated_data.get('floor', instance.floor)
        instance.name = validated_data.get('name', instance.name)
        instance.organization_zone = validated_data.get('organization_zone', instance.organization_zone)

        if cctv_data:
            for cctv in cctv_data:
                if not instance.cctv_camera.filter(name=cctv['name']).exists():
                    cctv_obj = ZoneCCTV.objects.create(name=cctv['name'])
                    instance.cctv_camera.add(cctv_obj)
        if document_data:
            for document in document_data:
                try:
                    file_str = document['document']
                except:
                    file_str = None
                if file_str:
                    try:
                        format, filestr = file_str.split(';base64,')
                        ext = format.split('/')[-1]
                        file_obj = ContentFile(base64.b64decode(filestr), name=document['name'] + "." + ext)
                    except:
                        raise ValidationError('unsupported file type, it should be Base64 format')
                else:
                    file_obj = None
                if not instance.document.filter(name=document['name']).exists():
                    document_obj, created = ZoneDocument.objects.get_or_create(name=document['name'], document=file_obj)
                    instance.document.add(document_obj)
        instance.save()
        return instance


class FindElevationSerializer(Serializer):
    latitude = CharField(label="Enter latitude")
    longitude = CharField(label="Enter longitude")
    elevation = CharField(read_only=True)

    def validate(self, data):
        lat = data.get("latitude", None)
        long = data.get("longitude", None)

        if not lat or not long:
            raise ValidationError("Missing latitude/longitude value")

        url = "https://maps.googleapis.com/maps/api/elevation/json?locations={0},{1}&key=AIzaSyAwVms24GcxE7bo9jG_iUPu-DE6wF0glzY".format(
            lat, long)

        response = requests.get(url)
        if response.status_code != 200:
            raise ValidationError("Google API returns %s" % response.status_code)
        try:
            response_data = json.loads(response.text)
            data['elevation'] = round(response_data['results'][0]['elevation'], 2)
        except Exception as e:
            raise ValidationError("Invalid response format with exception as %s" % e)
        return data

class OrganizationMessageSerializer(ModelSerializer):

    class Meta:
        model = OrganizationMessage
        fields = '__all__'

class GetOrganizationMessageSerializer(ModelSerializer):
    organization = ParentOrganizationDetailSerializer()
    class Meta:
        model = OrganizationMessage
        fields = '__all__'

class MuteOrganisationSerializer(ModelSerializer):
    class Meta:
        model = UserOrganization
        fields = (
            'is_muted',
        )


class UserOrganisationInfoSerializer(ModelSerializer):
    class Meta:
        model = UserOrganization
        fields = (
            'is_show_covid_info',
        )
