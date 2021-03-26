import json
import uuid
import re
import datetime
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, Http404
from rest_framework.permissions import (
    IsAuthenticated, AllowAny
)
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from .serializers import (
    IncidentLocationSerializer,
    EmergencyQuickContactAddSerializer)

from django.contrib.gis.geos import Point
from django.core.exceptions import ObjectDoesNotExist

from channels.layers import get_channel_layer

from ...reports.models import NotificationSettings, NotificationHistory

channel_layer = get_channel_layer()

from rest_framework.generics import (
    GenericAPIView,
    CreateAPIView,
    ListAPIView,
    UpdateAPIView,
    RetrieveAPIView,
    DestroyAPIView,
    RetrieveUpdateDestroyAPIView,
    ListCreateAPIView,
)
from rest_framework import pagination

from .serializers import (
    IncidentLocationSerializer, )

from .serializers import IncidentSerializer, IncidentResponderAlertSerializer, ResponderLocationSerializer, \
    EmergencyResponderLocationSerializer, EndOfIncidentSerializer, ResponderLocationUpdateSerializer, \
    JoinedRespondersListSerializer, OrganizersListSerializer, GetIncidentParamsSerializer, \
    IncidentLocationCheckoutSerializer, ReporterLocationTrackingSerializer, ResponderChangeLocationSerializer, \
    GetOrganizationZoneFloorSerializer, JoinedsReponderStreamSerializer, IncidentHistorySerializer, \
    IncidentContactsShareSerializer, IncidentOrganizationShareSerializer

from ..models import Incident, IncidentJoinedResponder, IncidentUrlTracker, ReporterLocationTracker
from fcm_django.models import FCMDevice

from apps.organization.models import OrganizationGeoFence, UserOrganization, OrganizationContact, EmergencyContact, \
    OrganizationProfile, Zone, ZoneFloor
from apps.organization.api.serializers import (
    OrganizationDetailSerializer, ZoneSerializer, OrganizationFloorsSerializer
)
from apps.accounts.api.utils import (
    send_push_notification,
    send_twilio_sms,
    send_incident_link_to_emergecy_contacts,
    send_incident_link_to_organization_contacts,
    send_incident_end_report,
)

from apps.incident.api.utils import save_incident_duration, send_user_notification
from asgiref.sync import async_to_sync

from rest_framework.serializers import (
    ValidationError,
)

User = get_user_model()


class ExamplePagination(pagination.PageNumberPagination):
    page_size = 1


class IncidentLocationAPIView(CreateAPIView):
    """
    APIView to identify in which organization the incident is happening
    :param : latitude, longitude
    :return : match status
    """
    serializer_class = IncidentLocationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = IncidentLocationSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = self.request.user
            incident = request.data.get('incident_id', None)
            latitude = float(request.data.get('latitude'))
            longitude = float(request.data.get('longitude'))
            incident_obj = None
            data = serializer.data
            user_org_objs = UserOrganization.objects.filter(user=user)
            org_objs = [obj.organization for obj in user_org_objs]
            point = Point(longitude, latitude)
            if incident:
                incident_obj = Incident.objects.get(id=incident)
            geofence_objs = OrganizationGeoFence.objects.filter(organization__in=org_objs,
                                                                co_ordinates__bbcontains=point, is_active=True)
            # check if the incident is inside current user's organizations
            if geofence_objs:
                data['status'] = "incident is happening on current user's organization"
                if incident_obj:
                    incident_obj.organization = geofence_objs[0].organization
                    incident_obj.save()
                organization_details = OrganizationDetailSerializer(geofence_objs[0].organization).data
                data['organization'] = organization_details
                return Response(data, status=HTTP_200_OK)

            geo_objs = OrganizationGeoFence.objects.filter(co_ordinates__bbcontains=point, is_active=True).exclude(
                organization__in=org_objs)
            # check if the incident is outside current user's organizations
            if geo_objs:
                data['status'] = "organization match found"
                if incident_obj:
                    incident_obj.organization = geo_objs[0].organization
                    incident_obj.save()
                organization_details = OrganizationDetailSerializer(geo_objs[0].organization).data
                data['organization'] = organization_details
                return Response(data, status=HTTP_200_OK)
            data = serializer.data
            data['status'] = 'not found'
            return Response(data, status=HTTP_200_OK)
        else:
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class IncidentListCreateAPIView(ListCreateAPIView):
    """
    API for create and list incidents
    """
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Incident.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, is_started=True)


class EmergencyContactIncidentsListAPIView(ListAPIView):
    """
       API list incidents for emergency contact users
    """
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        emergency_contacts_qs = EmergencyContact.objects.filter(
            Q(email=self.request.user.email) | Q(phone_number=self.request.user.phone_number))
        users = []
        if emergency_contacts_qs:
            for emergency_contact in emergency_contacts_qs:
                users.append(emergency_contact.user.id)
            return Incident.objects.filter(user__in=users, is_started=True)


class IncidentRetrieveUpdateDeleteAPIView(RetrieveUpdateDestroyAPIView):
    """
    Incident API to Retrieve/Update/Delete
    :param organization : Id of the organization
    """
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Incident.objects.all()

    def perform_update(self, serializer):
        notifications = NotificationHistory.objects.filter(requested_user=self.request.user, notification_type="responder_alert")
        for notify in notifications:
            if notify.attribute['id'] == self.kwargs['pk']:
                notify.attribute['emergency_message'] = self.request.data['emergency_message']
                notify.save()
        serializer.save(user=self.request.user)

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


    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        broad_cast_start_obj = instance.user_incident.first()
        broad_cast_current_obj = instance.user_incident.last()
        data['broadcast_start_time'] = None
        data['incident_start_location'] = None
        data['incident_current_location'] = None
        if broad_cast_start_obj:
            data['broadcast_start_time'] = broad_cast_start_obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
            data['incident_start_location'] = broad_cast_start_obj.address

        if broad_cast_current_obj:
            data['incident_current_location'] = broad_cast_current_obj.address
        return Response(data)


class IncidentRetrieveAPIView(RetrieveAPIView):
    """
    Incident API to Retrieve/Update/Delete
    :param organization : Id of the organization
    """
    serializer_class = IncidentSerializer

    def get_queryset(self):
        return Incident.objects.all()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        broad_cast_start_obj = instance.user_incident.first()
        broad_cast_current_obj = instance.user_incident.last()
        data['broadcast_start_time'] = None
        data['incident_start_location'] = None
        data['incident_current_location'] = None
        if broad_cast_start_obj:
            data['broadcast_start_time'] = broad_cast_start_obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
            data['incident_start_location'] = broad_cast_start_obj.address

        if broad_cast_current_obj:
            data['incident_current_location'] = broad_cast_current_obj.address
        return Response(data)


class EmergencyQuickContactAddAPIView(CreateAPIView):
    serializer_class = EmergencyQuickContactAddSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = EmergencyQuickContactAddSerializer(data=request.data, many=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save(user=request.user, status="Accepted", contact_type="Emergency")
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class IncidentRespondersAlertAPIView(CreateAPIView):
    """
    API to send alert notification to responders
    """
    serializer_class = IncidentResponderAlertSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_obj = request.user
        base_url = "https://web.samscloud.io/incident/dashboard/"
        emergency_contacts_exists = False
        organization_contacts_exists = False
        if IncidentResponderAlertSerializer(data=request.data).is_valid(raise_exception=True):
            pass
        incident_obj = Incident.objects.get(id=request.data.get("incident_id"))
        emergency_contacts_qs = EmergencyContact.objects.filter(user=user_obj, status="Accepted",
                                                                contact_type='Emergency')
        if emergency_contacts_qs.exists():
            emergency_contacts_exists = True
            for contact in emergency_contacts_qs:
                key_params = "?uuid=%s&stream=%s&incident=%s&latitude=%s&longitude=%s" % (
                    str(contact.uuid), incident_obj.streaming_id, incident_obj.id, incident_obj.latitude,
                    incident_obj.longitude)
                timestamp = datetime.datetime.now().strftime('%d%m%y%H%M%S')
                unique_key = uuid.uuid4().hex[:50].upper() + str(timestamp) + str(contact.uuid)[:4]
                IncidentUrlTracker.objects.create(key=unique_key, url=key_params)
                url = base_url + "?key=%s" % unique_key
                # url = base_url + "?uuid=%s&stream=%s&incident=%s&latitude=%s&longitude=%s" % (
                #     str(contact.uuid), incident_obj.wowza_streaming_id, incident_obj.id, incident_obj.latitude,
                #     incident_obj.longitude)
                if contact.phone_number and contact.phone_number != "":
                    qs = FCMDevice.objects.filter(
                        Q(user__email=contact.email) | Q(user__phone_number=contact.phone_number))
                    user_bj = User.objects.filter(Q(email=contact.email) | Q(phone_number=contact.phone_number)).first()
                else:
                    qs = FCMDevice.objects.filter(
                        Q(user__email=contact.email))
                    user_bj = User.objects.filter(Q(email=contact.email)).first()
                if user_bj:
                    setting = NotificationSettings.objects.filter(user=user_bj).first()
                    if qs.exists():
                        if setting.crisis_emergency_alert is True and setting.contact_has_incident is True:
                            fcm_obj = qs.first()
                            data = IncidentHistorySerializer(incident_obj, context={'request': request}).data
                            user_data = dict(data['user'])
                            data['user'] = user_data

                            message = "%s has been reporting an incident" % (user_obj.first_name)
                            title = "Incident Reporting"
                            data['contact_uuid'] = str(data['contact_uuid'])

                            history_data = IncidentHistorySerializer(incident_obj, context={'request': request}).data
                            history_data['contact_uuid'] = str(history_data['contact_uuid'])
                            histroy = NotificationHistory(user=user_bj, requested_user=user_obj,
                                                          requested_token=str(contact.uuid), attribute=history_data,
                                                          notification_type="responder_alert", message=message,
                                                          title=title)
                            histroy.save()
                            data["contact_uuid"] = contact.uuid
                            data["action"] = 'responder_alert'
                            send_push_notification.delay(fcm_obj.id, title, message, data)
                    if contact.phone_number and contact.phone_number != "" and setting.send_incident_text == True:
                        message = "%s  is reporting an incident, please click the link to view the live video feed and see their location %s" % (
                            user_obj.first_name, url)
                        to = contact.phone_number
                        send_twilio_sms.delay(message, to)
                    if contact.email and contact.email != "" and setting.send_incident_email == True:
                        send_incident_link_to_emergecy_contacts(contact.email, contact.name, user_obj, url)
                else:
                    if contact.phone_number and contact.phone_number != "":
                        message = "%s  is reporting an incident, please click the link to view the live video feed and see their location %s" % (
                            user_obj.first_name, url)
                        to = contact.phone_number
                        send_twilio_sms.delay(message, to)
                    if contact.email and contact.email != "":
                        send_incident_link_to_emergecy_contacts(contact.email, contact.name, user_obj, url)
        if incident_obj.organization:
            organization_contacts_qs = OrganizationContact.objects.filter(organization=incident_obj.organization)
            if organization_contacts_qs.exists():
                organization_contacts_exists = True
                for contact in organization_contacts_qs:

                    if contact.email != incident_obj.organization.email:
                        key_params = "?uuid=%s&stream=%s&incident=%s&latitude=%s&longitude=%s" % (
                            str(contact.uuid), incident_obj.streaming_id, incident_obj.id, incident_obj.latitude,
                            incident_obj.longitude)
                        timestamp = datetime.datetime.now().strftime('%d%m%y%H%M%S')
                        unique_key = uuid.uuid4().hex[:50].upper() + str(timestamp) + str(contact.uuid)[:4]
                        IncidentUrlTracker.objects.create(key=unique_key, url=key_params)
                        url = base_url + "?key=%s" % unique_key

                        # url = base_url + "?uuid=%s&stream=%s&incident=%s&latitude=%s&longitude=%s" % (
                        #     str(contact.uuid), incident_obj.wowza_streaming_id, incident_obj.id, incident_obj.latitude,
                        #     incident_obj.longitude)
                        qs = FCMDevice.objects.filter(
                            Q(user__email=contact.email) | Q(user__phone_number=contact.phone_number))

                        if User.objects.filter(
                                Q(email=contact.email) | Q(phone_number=contact.phone_number)).first():
                            user_bj = User.objects.filter(
                                Q(email=contact.email) | Q(phone_number=contact.phone_number)).first()
                            setting = NotificationSettings.objects.filter(user=user_bj).first()
                            if qs.exists():
                                if setting.crisis_emergency_alert == True and setting.contact_has_incident == True:
                                    fcm_obj = qs.first()

                                    data = IncidentHistorySerializer(incident_obj, context={'request': request}).data
                                    user_data = dict(data['user'])
                                    data['user'] = user_data
                                    message = "%s is reporting an incident" % (user_obj.first_name)
                                    title = "Incident Reporting"
                                    data['contact_uuid'] = str(data['contact_uuid'])
                                    history_data = IncidentHistorySerializer(incident_obj, context={'request': request}).data
                                    history_data['contact_uuid'] = str(history_data['contact_uuid'])
                                    histroy = NotificationHistory(user=user_bj, requested_user=user_obj,
                                                                  requested_token=str(contact.uuid), attribute=history_data,
                                                                  notification_type="responder_alert",
                                                                  message=message,
                                                                  title=title)
                                    histroy.save()
                                    data["contact_uuid"] = contact.uuid
                                    data["action"] = 'responder_alert'
                                    send_push_notification.delay(fcm_obj.id, title, message, data)
                            if contact.phone_number and contact.phone_number != "" and setting.send_incident_text == True:
                                message = "%s  is reporting an incident, please click the link to view the live video feed and see their location %s" % (
                                    user_obj.first_name, url)
                                to = contact.phone_number
                                send_twilio_sms.delay(message, to)
                            if contact.email and contact.email != "" and setting.send_incident_email == True:
                                send_incident_link_to_organization_contacts(contact.email, contact.name, user_obj, url)
                        else:
                            if contact.phone_number and contact.phone_number != "":
                                message = "%s  is reporting an incident, please click the link to view the live video feed and see their location %s" % (
                                    user_obj.first_name, url)
                                to = contact.phone_number
                                send_twilio_sms.delay(message, to)
                            if contact.email and contact.email != "":
                                send_incident_link_to_organization_contacts(contact.email, contact.name, user_obj, url)

        if organization_contacts_exists and emergency_contacts_exists:
            msg = "Notifications are sent to emergency and organization contacts"
        elif not organization_contacts_exists and emergency_contacts_exists:
            msg = "Notifications are sent to emergency contacts, organization contact list are empty"
        elif organization_contacts_exists and not emergency_contacts_exists:
            msg = "Notifications are sent to organization contacts, emergency contact list are empty, Please add emergency contact"
        else:
            msg = "No emergency and organization contacts are found"
        data = {'message': msg}
        return Response(data, status=HTTP_200_OK)


# class IncidentRespondersAlertAPIView(CreateAPIView):
#     """
#     API to send alert notification to responders
#     """
#     serializer_class = IncidentResponderAlertSerializer
#     permission_classes = [IsAuthenticated]
#
#     def post(self, request, *args, **kwargs):
#         user_obj = request.user
#         url = "some url"
#         emergency_contacts_exists = False
#         organization_contacts_exists = False
#         incident_obj = Incident.objects.get(id=request.data.get("incident_id"))
#         emergency_contacts_qs = EmergencyContact.objects.filter(user=user_obj, status="Accepted",
#                                                                 contact_type='Emergency').values_list("email",
#                                                                                                       "phone_number")
#         if emergency_contacts_qs.exists():
#             emergency_contacts_exists = True
#             email_lst, phone_lst = self.get_emails_phone_numbers_lst(emergency_contacts_qs)
#             user_qs = User.objects.filter(Q(email__in=email_lst) | Q(phone_number__in=phone_lst)).distinct()
#
#             for user in user_qs:
#                 try:
#                     fcm_obj = FCMDevice.objects.get(user=user)
#                     title = "Incident Reporting"
#                     message = "%s is reporting a incident." % user_obj.first_name
#                     data = {"url": url}
#                     send_push_notification.delay(fcm_obj.id, title, message, data)
#                 except ObjectDoesNotExist:
#                     if user.phone_number and user.phone_number != "":
#                         message = "%s is reporting a incident. please click on the url to watch %s" % (
#                             user_obj.first_name, url)
#                         to = user.phone_number
#                         send_twilio_sms.delay(message, to)
#                     else:
#                         send_incident_link_to_emergecy_contacts(user.email, user.first_name, user_obj, url)
#
#             user_qs_lst = user_qs.values_list("email", "phone_number")
#             user_emails, user_phones = self.get_emails_phone_numbers_lst(user_qs_lst)
#             rest_contact_emails = list(set(email_lst) - set(user_emails))
#             rest_contact_phone_numbers = list(set(phone_lst) - set(user_phones))
#             for email in rest_contact_emails:
#                 contact = EmergencyContact.objects.get(email=email)
#                 send_incident_link_to_emergecy_contacts(email, contact.name, user_obj, url)
#             for phone_number in rest_contact_phone_numbers:
#                 message = "%s is reporting a incident. please click on the url to watch %s" % (
#                     user_obj.first_name, url)
#                 to = phone_number
#                 send_twilio_sms.delay(message, to)
#         if incident_obj.organization:
#             organization_contacts_qs = OrganizationContact.objects.filter(
#                 organization=incident_obj.organization).values_list("email", "phone_number")
#             if organization_contacts_qs.exists():
#                 organization_contacts_exists = True
#                 email_lst, phone_lst = self.get_emails_phone_numbers_lst(organization_contacts_qs)
#                 user_qs = User.objects.filter(Q(email__in=email_lst) | Q(phone_number__in=phone_lst)).distinct()
#                 for user in user_qs:
#                     try:
#                         fcm_obj = FCMDevice.objects.get(user=user)
#                         title = "Incident Reporting"
#                         message = "%s is reporting a incident in your organization." % user_obj.first_name
#                         data = {"url": url}
#                         send_push_notification.delay(fcm_obj.id, title, message, data)
#                     except ObjectDoesNotExist:
#                         if user.phone_number and user.phone_number != "":
#                             message = "%s is reporting a incident in your organization. please click on the url to watch %s" % (
#                                 user_obj.first_name, url)
#                             to = user.phone_number
#                             send_twilio_sms.delay(message, to)
#                         else:
#                             send_incident_link_to_organization_contacts(user.email, user.first_name, user_obj, url)
#                 user_qs_lst = user_qs.values_list("email", "phone_number")
#                 user_emails, user_phones = self.get_emails_phone_numbers_lst(user_qs_lst)
#                 rest_contact_emails = list(set(email_lst) - set(user_emails))
#                 rest_contact_phone_numbers = list(set(phone_lst) - set(user_phones))
#                 for email in rest_contact_emails:
#                     contact = OrganizationContact.objects.get(email=email)
#                     send_incident_link_to_organization_contacts(email, contact.name, user_obj, url)
#                 for phone_number in rest_contact_phone_numbers:
#                     message = "%s is reporting a incident in your organization. please click on the url to watch %s" % (
#                         user_obj.first_name, url)
#                     to = phone_number
#                     send_twilio_sms.delay(message, to)
#         if organization_contacts_exists and emergency_contacts_exists:
#             msg = "Notifications are sent to emergency and organization contacts"
#         elif not organization_contacts_exists and emergency_contacts_exists:
#             msg = "Notifications are sent to emergency contacts, organization contact list are empty"
#         elif organization_contacts_exists and not emergency_contacts_exists:
#             msg = "Notifications are sent to organization contacts, emergency contact list are empty, Please add emergency contact"
#         else:
#             msg = "No emergency and organization contacts are found"
#         data = {'message': msg}
#         return Response(data, status=HTTP_200_OK)
#
#     def get_emails_phone_numbers_lst(self, qs):
#         qs_lst = list(zip(*qs))
#         qs_dict = dict(emails_lst=list(qs_lst[0]), phone_number_lst=list(qs_lst[1]))
#         emails_lst, phone_number_lst = qs_dict['emails_lst'], qs_dict['phone_number_lst']
#         emails_lst = [email for email in emails_lst if email and email != ""]
#         phone_number_lst = [phone_number for phone_number in phone_number_lst if phone_number and phone_number != ""]
#         return emails_lst, phone_number_lst


class RespondersListAPIView(ListAPIView):
    serializer_class = ResponderLocationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self, *args, **kwargs):
        incident_id = self.request.query_params.get('IncidentId', None)
        if incident_id:
            if not Incident.objects.filter(id=incident_id).exists():
                raise ValidationError("No detail found for this incident Id")
            organization_qs = Incident.objects.get(id=incident_id).organization
            query_set = OrganizationContact.objects.filter(organization=organization_qs)
            return query_set
        else:
            raise ValidationError("Incident Id id missing")

    def list(self, request, *args, **kwargs):
        serializer = self.serializer_class(self.get_queryset(), context={'request': request}, many=True)
        organization_data = serializer.data
        incident_id = request.query_params.get('IncidentId', None)
        incident_user = Incident.objects.get(id=incident_id).user
        emergency_objs = EmergencyContact.objects.filter(user=incident_user, status="Accepted",
                                                         contact_type="Emergency")
        emergency_data = EmergencyResponderLocationSerializer(emergency_objs, context={'request': request}, many=True)
        data = {'organization_contacts': organization_data, 'emergency_contacts': emergency_data.data}
        return Response(data, status=HTTP_200_OK)


class EndOfIncidentAPIView(CreateAPIView):
    serializer_class = EndOfIncidentSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = EndOfIncidentSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user_obj = self.request.user
            emergency_contacts_exists = False
            organization_contacts_exists = False
            incident_status = request.data.get("incident_status", None)
            msg = "Incident not ended"
            if incident_status == True:
                incident_obj = Incident.objects.get(id=request.data.get("incident_id"))
                reason = request.data.get("incident_ending_message", None)
                incident_obj.is_ended = True
                incident_obj.ending_message = reason
                incident_obj.save()

                emergency_contacts_qs = EmergencyContact.objects.filter(user=user_obj, status="Accepted",
                                                                        contact_type='Emergency')
                if emergency_contacts_qs.exists():
                    for contact_user in emergency_contacts_qs:
                        if contact_user.phone_number and contact_user.phone_number != "":
                            user_bj = User.objects.filter(
                                Q(email=contact_user.email) | Q(phone_number=contact_user.phone_number)).first()
                        else:
                            user_bj = User.objects.filter(Q(email=contact_user.email)).first()
                        if user_bj:
                            setting = NotificationSettings.objects.filter(user=user_bj).first()
                            emergency_contacts_exists = True
                            try:
                                user = User.objects.get(email=contact_user.email)
                                if setting.crisis_emergency_alert == True and setting.contact_has_incident == True:
                                    fcm_obj = FCMDevice.objects.get(user=user_bj)
                                    title = "Incident End Reporting"
                                    message = "%s has end the incident, %s. We recommend you check on them to ensure they’re ok." % (
                                        user_obj.first_name, request.data.get("incident_ending_message"))
                                    data = {"action":"incident_ended",
                                            "incident_id": str(incident_obj.id)}
                                    incident = Incident.objects.get(id=incident_obj.id)
                                    history_data = IncidentHistorySerializer(incident, context={'request': request}).data
                                    history_data['contact_uuid'] = str(history_data['contact_uuid'])
                                    histroy = NotificationHistory(user=user_bj, requested_user=user_obj, attribute=history_data,
                                                                  notification_type="incident_ended",
                                                                  message=message,
                                                                  title=title)
                                    histroy.save()
                                    send_push_notification.delay(fcm_obj.id, title, message, data)
                            except ObjectDoesNotExist:
                                pass
                            if contact_user.phone_number and contact_user.phone_number != "" and setting.send_incident_text == True:
                                message = "%s has end the incident, %s. We recommend you check on them to ensure they’re ok." % (
                                    user_obj.first_name, request.data.get("incident_ending_message"))
                                to = contact_user.phone_number
                                send_twilio_sms.delay(message, to)
                            if contact_user.email and contact_user.email != "" and setting.send_incident_email == True:
                                send_incident_end_report(contact_user.email, contact_user.name, user_obj, reason)
                        else:
                            if contact_user.phone_number and contact_user.phone_number != "":
                                message = "%s has end the incident, %s. We recommend you check on them to ensure they’re ok." % (
                                    user_obj.first_name, request.data.get("incident_ending_message"))
                                to = contact_user.phone_number
                                send_twilio_sms.delay(message, to)
                            if contact_user.email and contact_user.email != "":
                                send_incident_end_report(contact_user.email, contact_user.name, user_obj, reason)
                if incident_obj.organization:
                    organization_contacts_qs = OrganizationContact.objects.filter(
                        organization=incident_obj.organization).values_list("email", "phone_number")
                    if organization_contacts_qs.exists():
                        organization_contacts_exists = True
                        email_lst, phone_lst = self.get_emails_phone_numbers_lst(organization_contacts_qs)
                        user_qs = User.objects.filter(Q(email__in=email_lst) | Q(phone_number__in=phone_lst)).distinct()
                        for user in user_qs:
                            if User.objects.filter(
                                    Q(email=user.email) | Q(
                                        phone_number=user.phone_number)).first():
                                user_bj = User.objects.filter(
                                    Q(email=user.email) | Q(
                                        phone_number=user.phone_number)).first()
                                setting = NotificationSettings.objects.filter(user=user_bj).first()
                                try:
                                    if setting.crisis_emergency_alert == True and setting.contact_has_incident == True:
                                        fcm_obj = FCMDevice.objects.get(user=user)
                                        title = "Incident Reporting"
                                        message = "%s has end the incident, %s. We recommend you check on them to ensure they’re ok." % (
                                            user_obj.first_name, request.data.get("incident_ending_message"))
                                        data = {}
                                        incident = Incident.objects.get(id=incident_obj.id)
                                        history_data = IncidentHistorySerializer(incident, context={'request': request}).data
                                        history_data['contact_uuid'] = str(history_data['contact_uuid'])
                                        histroy = NotificationHistory(user=user_bj, requested_user=user_obj,
                                                                      attribute=history_data,
                                                                      notification_type="incident_ended",
                                                                      message=message,
                                                                      title=title)
                                        histroy.save()
                                        send_push_notification.delay(fcm_obj.id, title, message, data)
                                except ObjectDoesNotExist:
                                    pass
                                if user.phone_number and user.phone_number != "" and setting.send_incident_text == True:
                                    message = "%s has end the incident, %s. We recommend you check on them to ensure they’re ok." % (
                                        user_obj.first_name, request.data.get("incident_ending_message"))
                                    to = user.phone_number
                                    send_twilio_sms.delay(message, to)
                                if user.email and user.email != "" and setting.send_incident_email == True:
                                    send_incident_end_report(user.email, user.first_name, user_obj, reason)
                            else:
                                if user.phone_number and user.phone_number != "":
                                    message = "%s has end the incident, %s. We recommend you check on them to ensure they’re ok." % (
                                        user_obj.first_name, request.data.get("incident_ending_message"))
                                    to = user.phone_number
                                    send_twilio_sms.delay(message, to)
                                if user.email and user.email != "":
                                    send_incident_end_report(user.email, user.first_name, user_obj, reason)

                if organization_contacts_exists and emergency_contacts_exists:
                    msg = "Notifications are sent to emergency and organization contacts"
                elif not organization_contacts_exists and emergency_contacts_exists:
                    msg = "Notifications are sent to emergency contacts, organization contact list are empty"
                elif organization_contacts_exists and not emergency_contacts_exists:
                    msg = "Notifications are sent to organization contacts, emergency contact list are empty, Please add emergency contact"
                else:
                    msg = "No emergency and organization contacts are found"
            data = {'message': msg}
            return Response(data, status=HTTP_200_OK)

    def get_emails_phone_numbers_lst(self, qs):
        qs_lst = list(zip(*qs))
        qs_dict = dict(emails_lst=list(qs_lst[0]), phone_number_lst=list(qs_lst[1]))
        emails_lst, phone_number_lst = qs_dict['emails_lst'], qs_dict['phone_number_lst']
        emails_lst = [email for email in emails_lst if email and email != ""]
        phone_number_lst = [phone_number for phone_number in phone_number_lst if
                            phone_number and phone_number != ""]
        return emails_lst, phone_number_lst


class ResponderLocationUpdateAPIView(CreateAPIView):
    """
    API to update the Responder locations
    """
    serializer_class = ResponderLocationUpdateSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = ResponderLocationUpdateSerializer(data=request.data)
        uuid = request.data.get('uuid', None)
        incident_id = request.data.get('incident_id', None)
        latitude = request.data.get('latitude', None)
        longitude = request.data.get('longitude', None)
        altitude = request.data.get('altitude', None)
        if serializer.is_valid(raise_exception=True):
            organization_qs = OrganizationContact.objects.filter(uuid=uuid)
            emergency_qs = EmergencyContact.objects.filter(uuid=uuid)
            incident_obj = Incident.objects.get(id=incident_id)

            if organization_qs.exists():
                organization_obj = OrganizationContact.objects.get(uuid=uuid)
                organization_obj.latitude = latitude
                organization_obj.longitude = longitude
                organization_obj.altitude = altitude
                organization_obj.save()
                joined_responder_qs = IncidentJoinedResponder.objects.filter(user_incident_id=incident_id,
                                                                             organization_contact=organization_obj)
                if not joined_responder_qs.exists():
                    IncidentJoinedResponder.objects.create(user_incident=incident_obj,
                                                           organization_contact=organization_obj)
                    try:
                        fcm_obj = FCMDevice.objects.get(user=incident_obj.user)
                        title = "Responder is viewing"
                        message = "%s has join the incident." % organization_obj.name
                        data = {"name": organization_obj.name,
                                "latitude": organization_obj.latitude,
                                "longitude": organization_obj.longitude,
                                "altitude": organization_obj.altitude,
                                "type": "responder_joined"
                                }
                        user_obj = User.objects.filter(Q(email=organization_obj.email)).first()
                        if user_obj:
                            histroy = NotificationHistory(user=incident_obj.user, requested_user=user_obj,
                                                          notification_type="responder_joined", attribute=data,
                                                          message=message,
                                                          title=title)
                            histroy.save()
                        else:
                            histroy = NotificationHistory(user=incident_obj.user,
                                                          notification_type="responder_joined", attribute=data,
                                                          message=message,
                                                          title=title)
                            histroy.save()
                        send_push_notification.delay(fcm_obj.id, title, message, data)
                    except ObjectDoesNotExist:
                        pass
            elif emergency_qs.exists():
                emergency_obj = EmergencyContact.objects.get(uuid=uuid)
                emergency_obj.latitude = latitude
                emergency_obj.longitude = longitude
                emergency_obj.altitude = altitude
                emergency_obj.save()
                joined_responder_qs = IncidentJoinedResponder.objects.filter(user_incident_id=incident_id,
                                                                             emergency_contact=emergency_obj)
                if not joined_responder_qs.exists():
                    IncidentJoinedResponder.objects.create(user_incident=incident_obj,
                                                           emergency_contact=emergency_obj)
                    try:
                        fcm_obj = FCMDevice.objects.get(user=incident_obj.user)
                        title = "Responder is viewing"
                        message = "%s has join the incident." % emergency_obj.name
                        data = {
                            "name": emergency_obj.name,
                            "latitude": emergency_obj.latitude,
                            "longitude": emergency_obj.longitude,
                            "altitude": emergency_obj.altitude,
                            "type": "responder_joined"
                        }
                        user_obj = User.objects.filter(Q(email=emergency_obj.email)).first()
                        if user_obj:
                            histroy = NotificationHistory(user=incident_obj.user, requested_user=user_obj,
                                                          notification_type="responder_joined", attribute=data,
                                                          message=message,
                                                          title=title)
                            histroy.save()
                        else:
                            histroy = NotificationHistory(user=incident_obj.user,
                                                          notification_type="responder_joined", attribute=data,
                                                          message=message,
                                                          title=title)
                            histroy.save()
                        send_push_notification.delay(fcm_obj.id, title, message, data)
                    except ObjectDoesNotExist:
                        pass
            else:
                pass
            return Response(serializer.data, status=HTTP_200_OK)
        else:
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class JoinedRespondersListAPIView(ListAPIView):
    """
    API view to list all the joined responders of an incident
    """
    serializer_class = JoinedRespondersListSerializer

    def get_queryset(self, *args, **kwargs):
        incident_id = self.request.query_params.get('IncidentId', None)
        query_set = IncidentJoinedResponder.objects.filter(user_incident_id=incident_id)
        return query_set

    def list(self, request, *args, **kwargs):
        incident_id = self.request.query_params.get('IncidentId', None)
        emergency_contact_ids = self.get_queryset().exclude(emergency_contact=None).values_list('emergency_contact__id',
                                                                                                flat=True)
        organization_contact_ids = self.get_queryset().exclude(organization_contact=None).values_list(
            'organization_contact', flat=True)
        organization_contacts = OrganizationContact.objects.filter(id__in=organization_contact_ids)
        emergency_contacts = EmergencyContact.objects.filter(id__in=emergency_contact_ids)
        EmergencyContact.objects.filter(id__in=emergency_contact_ids)
        return Response({'emergency_contacts': EmergencyResponderLocationSerializer(emergency_contacts,
                        context={'request': request, 'incident_id': incident_id}, many=True).data,
                         'organization_contacts': ResponderLocationSerializer(organization_contacts,
                          context={'request': request, 'incident_id': incident_id}, many=True).data})


class OrganizersListApiView(ListAPIView):
    """
    API to list the organization within 50km radius
    """
    serializer_class = OrganizersListSerializer
    permission_classes = [AllowAny]
    queryset = OrganizationProfile.objects.all()

    def list(self, request, *args, **kwargs):
        latitude = self.request.query_params.get('Latitude', None)
        longitude = self.request.query_params.get('Longitude', None)
        if not latitude or not longitude:
            return Response({'status': 'Latitude/Longitude missing'}, status=HTTP_400_BAD_REQUEST)
        else:
            degrees = 50 / 111.325
            point = Point(float(longitude), float(latitude))
            geofence_qs = OrganizationGeoFence.objects.filter(co_ordinates__dwithin=(point, degrees))
            organization_qs = [obj.organization for obj in geofence_qs]
            data = OrganizersListSerializer(organization_qs, many=True).data
            return Response(data, status=HTTP_200_OK)


class GetIncidentParamsAPIView(ListAPIView):
    """
    API to get the incident url parameters
    """
    serializer_class = GetIncidentParamsSerializer
    permission_classes = [AllowAny]
    queryset = IncidentUrlTracker.objects.all()

    def list(self, request, *args, **kwargs):
        key_param = request.query_params.get('KeyParam', None)
        if key_param:
            if not IncidentUrlTracker.objects.filter(key=key_param).exists():
                return Response({'status': 'No detail found for this incident Id'}, status=HTTP_400_BAD_REQUEST)
            else:
                data = {}
                responder_type = "Not available"
                query_set = IncidentUrlTracker.objects.get(key=key_param).url
                uuid = re.findall(r'uuid=(.+?)&', query_set)[0]
                data['uuid'] = uuid
                data['stream'] = re.findall(r'stream=(.+?)&', query_set)[0]
                data['incident'] = re.findall(r'incident=(.+?)&', query_set)[0]
                data['latitude'] = re.findall(r'latitude=(.+?)&', query_set)[0]
                data['longitude'] = re.findall(r'longitude=(.+?)$', query_set)[0]
                if EmergencyContact.objects.filter(uuid=uuid).exists():
                    responder_type = "emergency_contact"
                if OrganizationContact.objects.filter(uuid=uuid).exists():
                    responder_type = "organization_contact"
                data['responder_type'] = responder_type
            return Response(data, status=HTTP_200_OK)
        else:
            return Response({'status': 'Key is missing'}, status=HTTP_400_BAD_REQUEST)


class IncidentCheckoutAPIView(CreateAPIView):
    """
        APIView to identify in which organization the incident is happening
        :param : latitude, longitude
        :return : match status
        """
    serializer_class = IncidentLocationCheckoutSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = IncidentLocationCheckoutSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            latitude = float(request.data.get('latitude'))
            longitude = float(request.data.get('longitude'))
            organization = request.data.get('organization_id', None)
            data = serializer.data
            point = Point(longitude, latitude)
            geofence_objs = OrganizationGeoFence.objects.filter(organization_id=organization,
                                                                co_ordinates__bbcontains=point, is_active=True)
            if not geofence_objs:
                data['status'] = 'User has been checkout from the organization'
            else:
                data['status'] = 'User still in the organization'
            return Response(data, status=HTTP_200_OK)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ReporterLocationTrackingAPIView(ListAPIView):
    """
    API to get reporter location that he/she covered during the incident
    :param : incident id as url parameter
    :return : list view of ReporterLocationTracker view
    """
    serializer_class = ReporterLocationTrackingSerializer
    permission_classes = [AllowAny]
    lookup_url_kwarg = 'pk'

    def get_queryset(self):
        incident_id = self.kwargs.get(self.lookup_url_kwarg)
        if not Incident.objects.filter(id=incident_id).exists():
            raise ValidationError("Incident does not exists")
        if not ReporterLocationTracker.objects.filter(reporter_incident_id=incident_id).exists():
            raise ValidationError("No reporter location has found for this incident")
        else:
            return [ReporterLocationTracker.objects.filter(reporter_incident_id=incident_id).order_by('-id').first()]


class GetResponderStreamAPIView(ListAPIView):
    serializer_class = JoinedRespondersListSerializer
    permission_classes = [AllowAny]
    lookup_url_kwarg = 'pk'

    def get_queryset(self):
        incident_id = self.kwargs.get(self.lookup_url_kwarg)
        if not Incident.objects.filter(id=incident_id).exists():
            raise ValidationError("Incident does not exists")
        if not IncidentJoinedResponder.objects.filter(user_incident_id=incident_id).exists():
            raise ValidationError("No responder has joined")
        else:
            return IncidentJoinedResponder.objects.filter(user_incident_id=incident_id)

    def list(self, request, *args, **kwargs):
        emergency_contacts = self.get_queryset().exclude(organization_contact=None)
        organization_contacts = self.get_queryset().exclude(emergency_contact=None)
        return Response({'emergency_contacts': JoinedRespondersListSerializer(organization_contacts, many=True).data,
                         'organization_contacts': JoinedRespondersListSerializer(emergency_contacts, many=True).data})


class GetOrganizationZoneFloorAPIView(CreateAPIView):
    """
    API to get sheared location's nearest organization, zone and floor
    :param : latitude, longitude, altitude
    :return : lorganization, zone and floor details
    """
    serializer_class = GetOrganizationZoneFloorSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = GetOrganizationZoneFloorSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            data = {}
            latitude = float(serializer.data['latitude'])
            longitude = float(serializer.data['longitude'])
            altitude = serializer.data['altitude']
            point = Point(longitude, latitude)
            geofence_objs = OrganizationGeoFence.objects.filter(co_ordinates__bbcontains=point, is_active=True)
            if geofence_objs:
                data['organization_name'] = geofence_objs[0].organization.organization_name
                data['organization_address'] = geofence_objs[0].organization.address
                data['organization_id'] = geofence_objs[0].organization.id
                zone_objs = Zone.objects.filter(organization=geofence_objs[0].organization)
                nearest_zone = self.get_nearest_zone(zone_objs, point)
                if nearest_zone:
                    zone_obj = nearest_zone['zone']
                    data['zone'] = zone_obj.name
                    data['zone_id'] = zone_obj.id
                    nearest_floor = self.get_nearest_floor(nearest_zone['zone'], altitude)
                    data.update(nearest_floor)
                return Response(data, status=HTTP_200_OK)
            else:
                data['status'] = 'Organization not found'
                return Response(data, status=HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

    def get_nearest_zone(self, zone_objs, point):
        distance_list = []
        nearest_zone = None
        for zone in zone_objs:
            zone_dict = {}
            distance = point.distance(zone.center_point)
            zone_dict["zone"] = zone
            zone_dict["distance"] = distance * 100
            distance_list.append(zone_dict)
        if distance_list:
            nearest_zone = sorted(distance_list, key=lambda i: i['distance'])[0]
        return nearest_zone

    def get_nearest_floor(self, zone_obj, altitude):
        floor_list = []
        data = {}
        zone_floor_objs = ZoneFloor.objects.filter(organization_zone=zone_obj)
        for zone_floor in zone_floor_objs:
            floor_dict = {}
            floor = zone_floor.floor
            floor_diff = float(altitude) - float(floor.altitude)
            if floor_diff <= 30:
                floor_dict['floor'] = floor
                floor_dict['diff'] = floor_diff
                floor_dict['zone_floor'] = zone_floor
                floor_list.append(floor_dict)
        if floor_list:
            nearest_floor = sorted(floor_list, key=lambda i: i['diff'])[0]
            data['zone_floor'] = nearest_floor['zone_floor'].name
            data['zone_floor_id'] = nearest_floor['zone_floor'].id
            data['floor_number'] = nearest_floor['floor'].floor_number
            data['floor_id'] = nearest_floor['floor'].id
        return data


class GetJoinedResponderByStreamIdAPIView(CreateAPIView):
    serializer_class = JoinedsReponderStreamSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = JoinedsReponderStreamSerializer(data=request.data)
        if serializer.is_valid():
            stream_id = request.data.get("stream_id", None)
            joined_responder_obj = IncidentJoinedResponder.objects.get(stream_id=stream_id)
            responder_type = None
            if joined_responder_obj.organization_contact:
                responder_obj = joined_responder_obj.organization_contact
                responder_type = "Organization Contact"
            if joined_responder_obj.emergency_contact:
                responder_obj = joined_responder_obj.emergency_contact
                responder_type = "Emergency Contact"
            data = {}
            data['responder_name'] = responder_obj.name
            responder_image = None
            qs = User.objects.filter(Q(email=responder_obj.email) | Q(phone_number=responder_obj.phone_number))
            if qs.exists():
                user_obj = qs.first()
                try:
                    responder_image = user_obj.profile_logo.url
                except:
                    responder_image = None
            data['responder_image'] = responder_image
            data['responder_type'] = responder_type
            data['stream_id'] = stream_id
            return Response(data, status=HTTP_200_OK)
        return Response(serializer.errors, HTTP_400_BAD_REQUEST)


@csrf_exempt
def antmedia_webhook(request):
    if request.method == "POST":
        stream_obj = None
        action = request.POST.get("action", None)
        if action == "vodReady":
            stream_id = request.POST.get("id", None)
            vod_id = request.POST.get("vodId", None)
            vod_name = request.POST.get("vodName", None)
            incident_qs = Incident.objects.filter(streaming_id=stream_id)
            if incident_qs.exists():
                stream_obj = incident_qs.first()
            responder_qs = IncidentJoinedResponder.objects.filter(stream_id=stream_id)
            if responder_qs.exists():
                stream_obj = responder_qs.first()
            if stream_obj:
                stream_obj.vod_id = vod_id
                stream_obj.vod_name = vod_name
                stream_obj.save()
                save_incident_duration(stream_obj.id, vod_id)
                return HttpResponse("VOD saved successfully", status=HTTP_200_OK)
            return HttpResponse("No Stream exists", status=HTTP_400_BAD_REQUEST)
        return HttpResponse("Different action", status=HTTP_400_BAD_REQUEST)


class IncidentHistoryListAPIView(ListAPIView):
    """
    API to list the incident histories of user
    """
    serializer_class = IncidentHistorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = pagination.LimitOffsetPagination

    def get_queryset(self, *args, **kwargs):
        user = self.request.user
        return Incident.objects.filter(Q(user=user, is_ended=True) | Q(user=user, is_stopped=True)).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        user = request.user
        email = user.email
        phone_number = user.phone_number
        # responder_objects = IncidentJoinedResponder.objects.filter(Q(emergency_contact__email=email) | Q(emergency_contact__phone_number=phone_number) | Q(organization_contact__email=email) | Q(organization_contact__phone_number=phone_number)).values('user_incident')
        # incident_objs = Incident.objects.filter(Q(user=user, is_ended=True) | Q(user=user, is_stopped=True) | Q(id__in=responder_objects, is_ended=True) | Q(id__in=responder_objects, is_stopped=True)).order_by('-created_at').distinct()
        incident_objs = Incident.objects.filter(Q(user=user, is_ended=True) | Q(user=user, is_stopped=True)).order_by('-created_at').distinct()
        data = IncidentHistorySerializer(incident_objs, context={'request': request}, many=True).data
        return Response(data, status=HTTP_200_OK)


class OngoingIncidentListAPIView(ListAPIView):
    """
    API to list the ongoing incidents of user
    """
    serializer_class = IncidentHistorySerializer
    permission_classes = [IsAuthenticated]
    queryset = Incident.objects.all()

    def list(self, request, *args, **kwargs):
        user = request.user
        email = user.email
        phone_number = user.phone_number
        if phone_number:
            responder_objects = IncidentJoinedResponder.objects.filter(Q(emergency_contact__email=email) | Q(emergency_contact__phone_number=phone_number) | Q(organization_contact__email=email) | Q(organization_contact__phone_number=phone_number)).values('user_incident')
        else:
            responder_objects = IncidentJoinedResponder.objects.filter(
                Q(emergency_contact__email=email) | Q(
                    organization_contact__email=email)).values(
                'user_incident')
        incident_objs = Incident.objects.filter(Q(user=user) | Q(id__in=responder_objects), is_ended=False,is_stopped=False, is_started=True).order_by('-created_at').distinct()
        data = IncidentHistorySerializer(incident_objs, context={'request': request}, many=True).data
        return Response(data, status=HTTP_200_OK)


class IncidentContactsShareAPIView(CreateAPIView):
    serializer_class = IncidentContactsShareSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = IncidentContactsShareSerializer(data=request.data, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            contacts = request.data.get('contacts')
            incident_obj = Incident.objects.get(id=request.data.get("incident"))
            user_obj = request.user
            data_list = []
            for contact in contacts:
                msg_dict = {}
                try:
                    contact_obj = EmergencyContact.objects.filter(id=contact)
                    if not contact_obj:
                        msg_dict[contact] = "no contacts present in this id"
                        data_list.append(msg_dict)
                    else:
                        contact_obj = contact_obj[0]
                        qs = FCMDevice.objects.filter(
                            Q(user__email=contact_obj.email) | Q(user__phone_number=contact_obj.phone_number))
                        if qs.exists():
                            fcm_obj = qs.first()
                            incident_data = IncidentHistorySerializer(incident_obj, context={'request': request}).data
                            user_data = dict(incident_data['user'])
                            incident_data['user'] = user_data
                            incident_data["contact_uuid"] = contact_obj.uuid
                            incident_data["action"] = 'incident_share'
                            message = "%s has been reporting an incident" % (user_obj.first_name)
                            title = "Incident Reporting"
                            send_push_notification.delay(fcm_obj.id, title, message, incident_data)
                            msg_dict[contact] = "Notification sent"
                            data_list.append(msg_dict)
                        else:
                            msg_dict[contact] = "fcm token missing"
                            data_list.append(msg_dict)
                except:
                    return Response({"data": "Error"}, status=HTTP_400_BAD_REQUEST)
        return Response({"data": data_list}, status=HTTP_200_OK)


class IncidentOrganizationShareAPIView(CreateAPIView):
    serializer_class = IncidentOrganizationShareSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = IncidentOrganizationShareSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            organizations = request.data.get('organizations')
            incident_id = request.data.get("incident")
            incident_obj = Incident.objects.get(id=incident_id)
            user_obj = request.user
            data_list = []
            for organization in organizations:
                msg_dict = {}
                try:
                    organization_obj = OrganizationProfile.objects.filter(id=organization)
                    if not organization_obj:
                        msg_dict[organization] = "no organization present in this id"
                        data_list.append(msg_dict)
                    else:
                        email = organization_obj[0].email
                        org_obj = OrganizationContact.objects.filter(organization_id=organization, email=email, contact_role='Owner')
                        if not org_obj:
                            msg_dict[organization] = "no contacts present in this id"
                            data_list.append(msg_dict)
                        else:
                            org_obj = org_obj[0]
                            qs = FCMDevice.objects.filter(
                                Q(user__email=org_obj.email) | Q(user__phone_number=org_obj.phone_number))
                            if qs.exists():
                                fcm_obj = qs.first()
                                incident_data = IncidentHistorySerializer(incident_obj, context={'request': request}).data
                                user_data = dict(incident_data['user'])
                                incident_data['user'] = user_data
                                incident_data["contact_uuid"] = org_obj.uuid
                                message = "%s has been reporting an incident" % (user_obj.first_name)
                                title = "Incident Reporting"
                                send_push_notification.delay(fcm_obj.id, title, message, incident_data)
                                msg_dict[organization] = "Notification sent"
                                data_list.append(msg_dict)
                            else:
                                msg_dict[organization] = "fcm token missing"
                                data_list.append(msg_dict)

                            # web socket for organization share
                            user_obj = User.objects.filter(Q(email=org_obj.email) | Q(phone_number=org_obj.phone_number))
                            if user_obj:
                                user_obj = user_obj[0]
                                user_id = user_obj.id
                                broadcast_room = f"user_{user_id}"
                                announcement_text = send_user_notification(incident_id, org_obj)
                                async_to_sync(channel_layer.group_send)(broadcast_room, {"type": "broadcast_message",
                                                                                         "text": announcement_text})


                except:
                    return Response({"data": "Error"}, status=HTTP_400_BAD_REQUEST)
        return Response({"data": data_list}, status=HTTP_200_OK)
