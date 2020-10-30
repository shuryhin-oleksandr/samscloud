import requests
import json
from rest_framework.serializers import (
    CharField,
    EmailField,
    ModelSerializer,
    ValidationError,
    Serializer,
    SerializerMethodField,
    BooleanField,
)
from rest_framework import serializers, pagination

from ..models import Incident, IncidentJoinedResponder, IncidentUrlTracker
from apps.organization.models import EmergencyContact, OrganizationContact, OrganizationProfile, OrganizationGeoFence
from apps.accounts.api.serializers import UserDetailUpdateSerializer, UserSerializer
from apps.organization.api.serializers import ParentOrganizationDetailSerializer, OrganizationGeoFenceSerializer
from django.contrib.auth import get_user_model
from apps.incident.models import ReporterLocationTracker
from django.db.models import Q

User = get_user_model()


class IncidentSerializer(ModelSerializer):
    user = UserDetailUpdateSerializer(read_only=True)

    class Meta:
        model = Incident
        exclude = ()


class IncidentLocationSerializer(Serializer):
    incident_id = CharField(label='Incident ID', required=False)
    latitude = CharField(label='Latitude')
    longitude = CharField(label='Longitude')

    def validate(self, data):
        if 'incident_id' in data:
            incident_id = data.get("incident_id", None)
            if not Incident.objects.filter(id=incident_id).exists():
                raise ValidationError("No detail found for this incident Id")
        return data


class EmergencyQuickContactAddSerializer(ModelSerializer):
    class Meta:
        model = EmergencyContact
        exclude = ('user', 'relationship', 'status', 'contact_type', 'uuid', 'latitude', 'longitude')


class IncidentResponderAlertSerializer(Serializer):
    # latitude = CharField(label='Latitude')
    # longitude = CharField(label='Longitude')
    incident_id = CharField(label="Enter Incident Id")

    def validate(self, data):
        incident_id = data.get("incident_id", None)
        if not Incident.objects.filter(id=incident_id).exists():
            raise ValidationError("No detail found for this incident Id")
        return data


class EmergencyResponderLocationSerializer(ModelSerializer):
    """
    Serializer to get location details from  emergency contact
    """
    profile_image = SerializerMethodField(read_only=True)
    start_location = SerializerMethodField(read_only=True)
    end_location = SerializerMethodField(read_only=True)

    class Meta:
        model = EmergencyContact
        exclude = ()

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

    def get_start_location(self, obj):
        user_obj = User.objects.filter(Q(email=obj.email) | Q(phone_number=obj.phone_number))
        if user_obj:
            incident_id = self.context.get("incident_id", None)
            try:
                user_location = ReporterLocationTracker.objects.filter(reporter_incident_id=incident_id,
                                                                       user=user_obj.first()).order_by('created_at')
                if user_location:
                    return ReporteTrackingSerializer(user_location.first()).data
            except:
                return None

    def get_end_location(self, obj):
        user_obj = User.objects.filter(Q(email=obj.email) | Q(phone_number=obj.phone_number))
        if user_obj:
            incident_id = self.context.get("incident_id", None)
            try:
                user_location = ReporterLocationTracker.objects.filter(reporter_incident_id=incident_id,
                                                                       user=user_obj.first()).order_by('-created_at')
                if user_location:
                    return ReporteTrackingSerializer(user_location.first()).data
            except:
                return None


class ResponderLocationSerializer(ModelSerializer):
    """
    Serializer to get location details from organization contacts
    """
    profile_image = SerializerMethodField(read_only=True)
    start_location = SerializerMethodField(read_only=True)
    end_location = SerializerMethodField(read_only=True)

    class Meta:
        model = OrganizationContact
        exclude = ()

    def get_start_location(self, obj):
        user_obj = User.objects.filter(Q(email=obj.email) | Q(phone_number=obj.phone_number))
        if user_obj:
            incident_id = self.context.get("incident_id", None)
            try:
                user_location = ReporterLocationTracker.objects.filter(reporter_incident_id=incident_id,
                                                                       user=user_obj.first()).order_by('created_at')
                if user_location:
                    return ReporteTrackingSerializer(user_location.first()).data
            except:
                return None

    def get_end_location(self, obj):
        user_obj = User.objects.filter(Q(email=obj.email) | Q(phone_number=obj.phone_number))
        if user_obj:
            incident_id = self.context.get("incident_id", None)
            try:
                user_location = ReporterLocationTracker.objects.filter(reporter_incident_id=incident_id,
                                                                       user=user_obj.first()).order_by('-created_at')
                if user_location:
                    return ReporteTrackingSerializer(user_location.first()).data
            except:
                return None

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


class EndOfIncidentSerializer(Serializer):
    incident_id = CharField(label="ID of the incident")
    incident_ending_message = CharField(label="Incident ending message")
    incident_status = BooleanField(label="Status of incident")

    def validate(self, data):
        incident_id = data.get("incident_id", None)
        if not Incident.objects.filter(id=incident_id).exists():
            raise ValidationError("No incident has found")
        return data


class ResponderLocationUpdateSerializer(Serializer):
    """
    Serializer to update the responders location
    """
    incident_id = CharField(label="ID of the incident")
    latitude = CharField(label="Latitude")
    longitude = CharField(label="Longitude")
    altitude = CharField(label="Altitude", allow_null=True, allow_blank=True, required=False)
    uuid = CharField(label="UUID")

    def validate(self, data):
        uuid = data.get('uuid', None)
        incident_id = data.get('incident_id', None)
        if not Incident.objects.filter(id=incident_id).exists():
            raise ValidationError("No incidents has found")
        organization_qs = OrganizationContact.objects.filter(uuid=uuid)
        emergency_qs = EmergencyContact.objects.filter(uuid=uuid)
        if not organization_qs.exists() and not emergency_qs:
            raise ValidationError("No matching contacts get")
        return data


class JoinedRespondersListSerializer(ModelSerializer):
    """
    Serializer to list all the joined responders of an incident
    """
    emergency_contact = EmergencyResponderLocationSerializer(read_only=True)
    organization_contact = ResponderLocationSerializer(read_only=True)

    class Meta:
        model = IncidentJoinedResponder
        exclude = ()


class OrganizersListSerializer(ModelSerializer):
    """
    Serializer to list all the organizations within 50 km radius
    """
    parent_organization_details = ParentOrganizationDetailSerializer(source='parent_organization')
    geofence = SerializerMethodField(read_only=True)

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
            'url',
            'organization_email',
            'address',
            'description',
            'who_can_join',
            'is_dispatch',
            'is_alert_sams',
            'is_email_verified',
            'number_of_floors',
            'geofence'
        ]

    def get_geofence(self, obj):
        try:
            geofence_obj = OrganizationGeoFence.objects.get(organization_id=obj.id)
            geofence_data = OrganizationGeoFenceSerializer(geofence_obj).data
        except:
            geofence_data = None
        return geofence_data


class GetIncidentParamsSerializer(ModelSerializer):
    """
    Serializer to get the incident url parameters
    """

    class Meta:
        model = IncidentUrlTracker
        exclude = ()


class IncidentLocationCheckoutSerializer(Serializer):
    organization_id = CharField(label='Organization ID')
    latitude = CharField(label='Latitude')
    longitude = CharField(label='Longitude')

    def validate(self, data):
        if 'organization_id' in data:
            org_id = data.get("organization_id", None)
            if not OrganizationProfile.objects.filter(id=org_id).exists():
                raise ValidationError("No detail found for this Organization Id")
        return data


class ReporterLocationTrackingSerializer(ModelSerializer):
    """
    Serializer for ReporterLocationTracker
    """

    class Meta:
        model = ReporterLocationTracker
        fields = '__all__'


class ReporteTrackingSerializer(ModelSerializer):
    """
    Serializer for ReporterLocationTracker
    """

    class Meta:
        model = ReporterLocationTracker
        fields = ['latitude', 'longitude', 'altitude', 'address']


class ResponderChangeLocationSerializer(ModelSerializer):
    """
    Serializer to Incident Joined responders
    """

    class Meta:
        model = IncidentJoinedResponder


class GetOrganizationZoneFloorSerializer(Serializer):
    """
    Serializer to get organization , zone, floor details
    """
    latitude = CharField(label='Latitude')
    longitude = CharField(label='Longitude')
    altitude = CharField(label='Altitude')


class JoinedsReponderStreamSerializer(Serializer):
    stream_id = CharField(label="stream Id of the user")

    def validate(self, data):
        stream_id = data.get('stream_id')
        if not stream_id:
            raise ValidationError("Stream id not found")
        if not IncidentJoinedResponder.objects.filter(stream_id=stream_id).exists():
            raise ValidationError("No stream Id has found")
        return data


class IncidentHistorySerializer(ModelSerializer):
    created_date = SerializerMethodField()
    updated_date = SerializerMethodField()
    broadcast_start_time = SerializerMethodField()
    user = UserDetailUpdateSerializer(read_only=True)
    current_location = SerializerMethodField()
    stream_url = SerializerMethodField()
    stream_duration = SerializerMethodField()
    preview_thumbnail = SerializerMethodField()
    contact_uuid = SerializerMethodField()
    start_location = SerializerMethodField()
    end_location = SerializerMethodField()


    class Meta:
        model = Incident
        fields = ['id', 'user', 'is_started', 'is_ended', 'is_stopped', 'emergency_message', 'address', 'streaming_id',
                  'created_date', 'updated_date', 'current_location', 'broadcast_start_time', 'stream_url',
                  'stream_duration', 'preview_thumbnail', 'contact_uuid', 'start_location', 'end_location', 'ending_message']

    def get_start_location(self, obj):
        user_location = ReporterLocationTracker.objects.filter(reporter_incident=obj, user=obj.user).order_by('created_at')
        if user_location:
            return ReporteTrackingSerializer(user_location.first()).data
        return None

    def get_end_location(self, obj):
        user_location = ReporterLocationTracker.objects.filter(reporter_incident=obj, user=obj.user).order_by('-created_at')
        if user_location:
            return ReporteTrackingSerializer(user_location.first()).data
        return None

    def get_created_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')

    def get_updated_date(self, obj):
        return obj.updated_at.strftime('%Y-%m-%d %H:%M:%S')

    def get_preview_thumbnail(self, obj):
        request = self.context.get("request", None)
        if obj.stream_thumbnail and obj.stream_thumbnail.url != None:
            return request.build_absolute_uri(obj.stream_thumbnail.url)

    def get_stream_duration(self, obj):
        time = None
        duration = obj.stream_duration
        if duration:
            time = float(duration)/1000
            time = round(time, 2)
        return time

    def get_broadcast_start_time(self, obj):
        broad_cast_start_obj = obj.user_incident.first()
        broadcast_start_time = None
        if broad_cast_start_obj:
            broadcast_start_time = broad_cast_start_obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
        return broadcast_start_time

    def get_current_location(self, obj):
        incident_current_location = None
        broad_cast_current_obj = obj.user_incident.last()
        if broad_cast_current_obj:
            incident_current_location = broad_cast_current_obj.address
        return incident_current_location

    def get_stream_url(self, obj):
        vod_name = obj.vod_name
        url = None
        if vod_name:
            if '.mp4' not in vod_name:
                url = 'https://ant-media-storage.s3-us-west-2.amazonaws.com/streams/'+ vod_name +'.mp4'
            else:
                url = 'https://ant-media-storage.s3-us-west-2.amazonaws.com/streams/' + vod_name
        return url

    def get_contact_uuid(self, obj):
        request = self.context.get('request', None)
        if request:
            email = request.user.email
            phone_number = request.user.phone_number
            emergency_objs = EmergencyContact.objects.filter(Q(email=email) | Q(phone_number=phone_number)).distinct()
            org_objs = OrganizationContact.objects.filter(Q(email=email) | Q(phone_number=phone_number)).distinct()
            if emergency_objs:
                uuid = emergency_objs[0].uuid
                return uuid
            elif org_objs:
                uuid = org_objs[0].uuid
                return uuid
        else:
            return None



class IncidentContactsShareSerializer(Serializer):
    incident = CharField(label="Icident ID")
    contacts = serializers.ListField(required=True)

    def validate(self, data):
        incident_id = data.get('incident', None)
        contacts = data.get('contacts', None)
        if not Incident.objects.filter(id=incident_id).exists():
            raise ValidationError("Invalid Incident ID found")
        if len(contacts) == 0:
            raise ValidationError("Contacts list is empty")
        return data


class IncidentOrganizationShareSerializer(Serializer):
    incident = CharField(label="Icident ID")
    organizations = serializers.ListField(required=True)

    def validate(self, data):
        incident_id = data.get('incident', None)
        organizations = data.get('organizations', None)
        if not Incident.objects.filter(id=incident_id).exists():
            raise ValidationError("Invalid Incident ID found")
        if len(organizations) == 0:
            raise ValidationError("Organizations list is empty")
        return data

