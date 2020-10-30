from django.db.models import Q
from fcm_django.models import FCMDevice
from rest_framework.serializers import (
    ModelSerializer, Serializer, ValidationError
)
from django.contrib.auth import get_user_model
from rest_framework import serializers
from ..models import ReportType, Report, ReportFile, UserGeofences, NotificationHistory, UserGeofenceStatus, \
    NotificationSettings
from apps.organization.models import OrganizationProfile, ZoneFloor, Zone, EmergencyContact
from apps.accounts.api.serializers import UserListSerializer, UserDetailUpdateSerializer, \
    EmergencyContactDetailsSerializer
from apps.accounts.api.utils import send_push_notification
from rest_framework.fields import CharField

User = get_user_model()


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email']

class OrganizationSerializer(ModelSerializer):
    class Meta:
        model = OrganizationProfile
        fields = ['id', 'organization_name', 'address', 'latitude', 'longitude', 'logo']


class ZonefloorSerializer(ModelSerializer):
    class Meta:
        model = ZoneFloor
        fields = ['id', 'name']


class ZoneSerializer(ModelSerializer):
    class Meta:
        model = Zone
        fields = ['id', 'name']


class ReportTypeSerializer(ModelSerializer):

    class Meta:
        model = ReportType
        exclude = ()


class ReportFilesSerializer(Serializer):
    file_report = serializers.CharField(required=True)
    video1 = serializers.FileField(required=False)
    video2 = serializers.FileField(required=False)
    image1 = serializers.FileField(required=False)
    image2 = serializers.FileField(required=False)
    image3 = serializers.FileField(required=False)
    image4 = serializers.FileField(required=False)

    def validate(self, attrs):
        report_id = attrs.get('file_report', None)
        if not Report.objects.filter(id=report_id).exists():
            raise ValidationError("incorrect Report ID")
        return attrs


class ReportSerializer(ModelSerializer):
    reporting_organizations = OrganizationSerializer(many=True, required=False)
    organization = OrganizationSerializer(required=False)
    report_zone = ZoneSerializer(required=False)
    report_zone_floor = ZonefloorSerializer(required=False)
    user = UserSerializer(required=False)
    report_type = serializers.SerializerMethodField(read_only=True)
    report_type_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Report
        fields = '__all__'

    def get_report_type(self, obj):
        return obj.report_type.name

    def get_report_type_id(self, obj):
        return obj.report_type.id



class ReportCreateSerializer(ModelSerializer):
    user = serializers.CharField(read_only=True)
    maintenance_id = serializers.CharField(read_only=True)
    reporting_organizations = serializers.ListField(required=False)


    class Meta:
        model = Report
        fields = '__all__'

    def validate(self, attrs):
        organizations = attrs.get('reporting_organizations', None)
        if organizations:
            org_objs = OrganizationProfile.objects.filter(id__in=organizations)
            if len(organizations) != len(org_objs):
                raise ValidationError("incorrect organization ID present in the list")
        return attrs

    def create(self, validated_data):
        organizations = validated_data.pop('reporting_organizations', None)
        report = Report.objects.create(**validated_data)
        if organizations:
            org_objs = OrganizationProfile.objects.filter(id__in=organizations)
            report.reporting_organizations.set(org_objs)
        return report

    def update(self, instance, validated_data):
        organizations = validated_data.pop('reporting_organizations', None)
        zone = validated_data.pop('report_zone', None)
        zone_floor = validated_data.pop('report_zone_floor', None)
        report_type = validated_data.pop('report_type', None)
        if report_type:
            report_type_obj = ReportType.objects.get(id=report_type)
            instance.report_type = report_type_obj
        if zone:
            zone_obj = Zone.objects.get(id=zone)
            instance.report_zone = zone_obj
        if zone_floor:
            zone_floor_obj = ZoneFloor.objects.get(id=zone_floor)
            instance.report_zone_floor = zone_floor_obj

        instance.details = validated_data.get('details', instance.details)
        instance.address = validated_data.get('address', instance.address)
        instance.latitude = validated_data.get('latitude', instance.latitude)
        instance.longitude = validated_data.get('longitude', instance.longitude)
        instance.send_anonymously = validated_data.get('send_anonymously', instance.send_anonymously)
        if organizations:
            org_objs = OrganizationProfile.objects.filter(id__in=organizations)
            for org_obj in org_objs:
                instance.reporting_organizations.add(org_obj)
        instance.save()
        return instance


class UserGeoFenceSerializer(ModelSerializer):
    """
    User geofence serializer
    """

    class Meta:
        model = UserGeofences
        fields = "__all__"
        read_only_fields = ("id", "user",)

    def create(self, validated_data):
        assign_contacts = validated_data.pop('assign_contacts')
        assign_mangers = validated_data.pop('assign_mangers')
        geos = UserGeofences.objects.create(**validated_data)
        for tg in assign_contacts:
            geos.assign_contacts.add(tg)
        for tgs in assign_mangers:
            geos.assign_mangers.add(tgs)
        if geos.assign_contacts:
            for contact_obj in geos.assign_contacts.all():
                if contact_obj.email is not None:
                    user_obj = User.objects.filter(email=contact_obj.email)
                if contact_obj.phone_number is not None:
                    user_obj = User.objects.filter(phone_number=contact_obj.phone_number)
                if user_obj is not None:
                    print(user_obj)
                    qs = FCMDevice.objects.filter(user=user_obj.first())
                    if qs.exists():
                        fcm_obj = qs.first()
                        data = {
                            "type": "geofence-request-check-in",
                            "emergency-contact": contact_obj.id,
                            "geo-fence": geos.id,
                            "geofence-type": "Contact"
                        }
                        message = "%s is requesting a geo fence check-in" % (
                            geos.user.first_name)
                        title = "Request to Geo Fence checkIn"
                        send_push_notification.delay(fcm_obj.id, title, message, data)
                        histroy = NotificationHistory(user=user_obj.first(), requested_user=geos.user,
                                                      attribute=data,
                                                      notification_type="request-geofence-check-in", message=message,
                                                      title=title)
                        histroy.save()
        if geos.assign_mangers:
            for contact_obj in geos.assign_mangers.all():
                if contact_obj.email is not None:
                    user_obj = User.objects.filter(email=contact_obj.email)
                if contact_obj.phone_number is not None:
                    user_obj = User.objects.filter(phone_number=contact_obj.phone_number)
                if user_obj is not None:
                    qs = FCMDevice.objects.filter(user=user_obj.first())
                    if qs.exists():
                        fcm_obj = qs.first()
                        data = {
                            "type": "geofence-request-check-in",
                            "emergency-contact": contact_obj.id,
                            "geo-fence": geos.id,
                            "geofence-type": "Manager"
                        }
                        message = "%s is requesting a geo fence check-in" % (
                            geos.user.first_name)
                        title = "Request to Geo Fence checkIn"
                        send_push_notification.delay(fcm_obj.id, title, message, data)
                        histroy = NotificationHistory(user=user_obj.first(), requested_user=geos.user,
                                                      attribute=data,
                                                      notification_type="request-geofence-check-in", message=message,
                                                      title=title)
                        histroy.save()

        return geos


    def update(self, instance, validated_data):
        assign_mangers = validated_data.pop('assign_mangers', None)
        assign_contacts = validated_data.pop('assign_contacts', None)
        instance.name = validated_data.get('name', instance.name)
        instance.location = validated_data.get('location', instance.location)
        instance.radius = validated_data.get('radius', instance.radius)
        instance.from_time = validated_data.get('from_time', instance.from_time)
        instance.to_time = validated_data.get('to_time', instance.to_time)
        instance.latitude = validated_data.get('latitude', instance.latitude)
        instance.longitude = validated_data.get('longitude', instance.longitude)
        if assign_contacts:
            instance.assign_contacts.clear()
            for tgs in assign_contacts:
                instance.assign_contacts.add(tgs)
        else:
            instance.assign_contacts.clear()
        if assign_mangers:
            instance.assign_mangers.clear()
            for tgs in assign_mangers:
                instance.assign_mangers.add(tgs)
        else:
            instance.assign_mangers.clear()
        instance.save()
        if instance.assign_contacts:
            for contact_obj in instance.assign_contacts.all():
                if contact_obj.email is not None:
                    user_obj = User.objects.filter(email=contact_obj.email)
                if contact_obj.phone_number is not None:
                    user_obj = User.objects.filter(phone_number=contact_obj.phone_number)
                if user_obj is not None:
                    status = UserGeofenceStatus.objects.filter(user=user_obj.first(), geofence=instance,
                                                               contact_type="Contact")
                    if not status:
                        qs = FCMDevice.objects.filter(user=user_obj.first())
                        if qs.exists():
                            fcm_obj = qs.first()
                            data = {
                                "type": "geofence-request-check-in",
                                "emergency-contact": contact_obj.id,
                                "geo-fence": instance.id,
                                "geofence-type": "Contact"
                            }
                            message = "%s is requesting a geo fence check-in" % (
                                instance.user.first_name)
                            title = "Request to Geo Fence checkIn"
                            send_push_notification.delay(fcm_obj.id, title, message, data)
                            histroy = NotificationHistory(user=user_obj.first(), requested_user=instance.user,
                                                          attribute=data,
                                                          notification_type="request-geofence-check-in",
                                                          message=message,
                                                          title=title)
                            histroy.save()
        if instance.assign_mangers:
            for contact_obj in instance.assign_mangers.all():
                if contact_obj.email is not None:
                    user_obj = User.objects.filter(email=contact_obj.email)
                if contact_obj.phone_number is not None:
                    user_obj = User.objects.filter(phone_number=contact_obj.phone_number)
                if user_obj is not None:
                    status = UserGeofenceStatus.objects.filter(user=user_obj.first(), geofence=instance,
                                                               contact_type="Manager")
                    if not status:
                        qs = FCMDevice.objects.filter(user=user_obj.first())
                        if qs.exists():
                            fcm_obj = qs.first()
                            data = {
                                "type": "geofence-request-check-in",
                                "emergency-contact": contact_obj.id,
                                "geo-fence": instance.id,
                                "geofence-type": "Manager"
                            }
                            message = "%s is requesting a geo fence check-in" % (
                                instance.user.first_name)
                            title = "Request to Geo Fence checkIn"
                            send_push_notification.delay(fcm_obj.id, title, message, data)
                            histroy = NotificationHistory(user=user_obj.first(), requested_user=instance.user,
                                                          attribute=data,
                                                          notification_type="request-geofence-check-in", message=message,
                                                          title=title)
                            histroy.save()
        return instance

class ListUserGeoFenceSerializer(ModelSerializer):
    """
    User Report serializer
    """
    user = UserDetailUpdateSerializer()
    assign_contacts = EmergencyContactDetailsSerializer(many=True)
    assign_mangers = EmergencyContactDetailsSerializer(many=True)
    class Meta:
        model = UserGeofences
        fields = "__all__"
        read_only_fields = ("id", "user", "assign_contacts", "assign_mangers",)

class UserGeoFenceSActivateSerializer(Serializer):
    """
    Serializer to activate the UserGeoFence
    """
    emergency_id = CharField(label="Enter Emergency Id")
    geofence_id = CharField(label="Enter Geo Fence Id")
    status = CharField(label='Status')
    type = CharField(label='Type')

    def validate(self, data):
        contact_obj = EmergencyContact.objects.filter(id=int(data.get('emergency_id'))).first()
        if not contact_obj:
            raise serializers.ValidationError('There is no emergency contact with this ID')

        else:
            if data.get('type') == 'Contact':
                geofence = UserGeofences.objects.filter(id=int(data.get('geofence_id')), assign_contacts__id=contact_obj.id)
                if not geofence:
                    raise serializers.ValidationError('There is no  Geo Fence with this ID')
                else:
                    return data
            if data.get('type') == 'Manager':
                geofence = UserGeofences.objects.filter(id=int(data.get('geofence_id')), assign_mangers__id=contact_obj.id)
                if not geofence:
                    raise serializers.ValidationError('There is no  Geo Fence with this ID')
                else:
                    return data

class HideGeofenceSerializer(ModelSerializer):
    class Meta:
        model = UserGeofenceStatus
        fields = (
            'is_hidden',
        )

    def update(self, instance, validated_data):
        instance.is_hidden = validated_data.get('is_hidden', instance.is_hidden)
        instance.save()
        user = self.context['request'].user
        geofence = instance.geofence
        if instance.is_hidden == True:
            qs = FCMDevice.objects.filter(
                Q(user__email=geofence.user.email) | Q(user__phone_number=geofence.user.phone_number))
            if User.objects.filter(Q(email=geofence.user.email) | Q(phone_number=geofence.user.phone_number)).first():
                user_bj = User.objects.filter(
                    Q(email=geofence.user.email) | Q(phone_number=geofence.user.phone_number)).first()
                if qs.exists():
                    fcm_obj = qs.first()

                    data = {}

                    message = "%s is no longer sharing location in %s" % (user.first_name, geofence.name)
                    title = "Geo Fence stop Sharing"
                    histroy = NotificationHistory(user=user_bj, requested_user=user,
                                                  attribute=data,
                                                  notification_type="geofence_stop_sharing", message=message,
                                                  title=title)
                    histroy.save()
                    data["action"] = 'geofence_stop_sharing'
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

                                data = {}

                                message = "%s is no longer sharing location in %s" % (
                                    user.first_name, geofence.name)
                                title = "Geo Fence stop Sharing"
                                histroy = NotificationHistory(user=user_bj, requested_user=user,
                                                              attribute=data,
                                                              notification_type="geofence_stop_sharing", message=message,
                                                              title=title)
                                histroy.save()
                                data["action"] = 'geofence_stop_sharing'
                                send_push_notification.delay(fcm_obj.id, title, message, data)
        return instance

class GeofenceResponderAlertSerializer(Serializer):
    # latitude = CharField(label='Latitude')
    geofence_status = CharField(label='Geo Fence Status')
    contact_type = CharField(label='Contact Type')
    geofence_id = CharField(label="Enter Geo Fence Id")

    def validate(self, data):
        geofence_id = data.get("geofence_id", None)
        if not UserGeofences.objects.filter(id=geofence_id).exists():
            raise ValidationError("No detail found for this Geofence Id")
        return data

class HideGeofenceCheckinSerializer(Serializer):
    # latitude = CharField(label='Latitude')
    contact_type = CharField(label='Contact Type')
    geofence_id = CharField(label="Enter Geo Fence Id")

    def validate(self, data):
        geofence_id = data.get("geofence_id", None)
        if not UserGeofences.objects.filter(id=geofence_id).exists():
            raise ValidationError("No detail found for this Geofence Id")
        return data
