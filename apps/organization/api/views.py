from django.contrib.auth import get_user_model
from django.views.generic import ListView
from fcm_django.models import FCMDevice
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from ..models import OrganizationProfile, UserOrganization, OrganizationType, OrganizationContact, EmergencyContact, \
    OrganizationAddress, OrganizationFloors, OrganizationGeoFence, ZoneCCTV, ZoneDocument, Zone, ZoneFloor, \
    OrganizationMessage

import json
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    UpdateAPIView,
    RetrieveAPIView,
    DestroyAPIView,
    RetrieveUpdateDestroyAPIView,
    ListCreateAPIView, RetrieveUpdateAPIView, get_object_or_404,
)

from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAdminUser,
    IsAuthenticatedOrReadOnly,
)

from .serializers import (
    ParentOrganizationProfileSerializer,
    OrganizationUpdateSerializer,
    OrganizationDetailSerializer,
    UserOrganizationListSerializer,
    OrganizationContactAddSerializer,
    CheckProCodeSerializer,
    OrganizationTypeSerializer,
    OrganizationContactListSerializer,
    OrganizationContactDetailUpdateDeleteSerializer,
    OrganizationAddAddressSerializer,
    OrganizationFloorsSerializer,
    OrganizationGeoFenceSerializer,
    ZoneCCTVSerializer,
    ZoneDocumentSerializer,
    ZoneSerializer,
    UserOrganizationCreateSerializer,
    OrganizationEmailActivationSerializer,
    OrganizationListSerializer,
    GetOrganizationByProCodeSerializer,
    OrganizationAddressListSerializer,
    ZoneFloorSerializer,
    FindElevationSerializer,
    ZoneCCTVDeleteSerializer,
    ZoneCCTVGetSerializer,
    OrganizationListForLoginSerializer, OrganizationMessageSerializer, GetOrganizationMessageSerializer,
    MuteOrganisationSerializer, UserOrganisationInfoSerializer)

from apps.accounts.api.utils import (send_organization_activation_email,
                                     send_emergency_contact_mail,
                                     send_organization_email_activation, send_push_notification)
from ...reports.models import NotificationHistory

User = get_user_model()


class ParentOrganizationProfileCreateAPIView(CreateAPIView):
    serializer_class = ParentOrganizationProfileSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        email = request.data.get('email', None)
        contacts = request.data.get('contacts', None)
        contact_name = request.data.get('contact_name', None)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization_obj = serializer.save()
        data = serializer.data
        if email:
            email = email.lower().strip()
            if User.objects.filter(email=email).exists():
                user_obj = User.objects.get(email=email)
            else:
                user_obj = User.objects.create(email=email, first_name=contact_name, user_type='Responder')
            if not user_obj.is_verified:
                send_organization_activation_email(self.request, user_obj, organization_obj)
                data['already_verified'] = False
                data['is_verification_mail_send'] = True
            else:
                data['already_verified'] = True
                data['is_verification_mail_send'] = False
                UserOrganization.objects.create(user=user_obj, organization=organization_obj)
        if contacts and contacts != '':
            if isinstance(contacts, str):
                contacts = json.loads(contacts)
            for cont in contacts:
                cont.update({"organization": organization_obj.id})
            contact_serializer = OrganizationContactAddSerializer(data=contacts, many=True,
                                                                  context={'request': request})
            if contact_serializer.is_valid(raise_exception=True):
                contact_serializer.create(validated_data=contacts)
                data['contacts'] = contact_serializer.data
        headers = self.get_success_headers(serializer.data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)


class UserOrganizationListAPIView(ListAPIView):
    serializer_class = UserOrganizationListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self, *args, **kwargs):
        return UserOrganization.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        serializer = self.serializer_class(self.get_queryset(), many=True)
        data = serializer.data
        new_res = []
        for i in range(0, len(data)):
            data[i]['organization']['is_show_covid_info'] = data[i]['is_show_covid_info']
            new_res.append(data[i]['organization'])
        return Response(new_res, status=HTTP_200_OK)


class OrganizationUpdateAPIView(UpdateAPIView):
    serializer_class = OrganizationUpdateSerializer
    permission_classes = [IsAuthenticated]
    queryset = OrganizationProfile.objects.all()

    def partial_update(self, request, *args, **kwargs):
        contacts = request.data.get('contacts', None)
        organization_email = request.data.get('organization_email', None)
        organization_obj = self.get_object()
        serializer = OrganizationUpdateSerializer(organization_obj, data=request.data, partial=True,
                                                  context={"organization_id": organization_obj.id, "request": request})
        if serializer.is_valid(raise_exception=True):
            organization_obj = serializer.save()
            data = serializer.data
            if organization_email and not organization_obj.is_email_verified:
                try:
                    user_obj = User.objects.get(email=organization_email)
                    if user_obj.is_verified:
                        organization_obj.is_email_verified = True
                        organization_obj.save()
                    else:
                        send_organization_email_activation(request, organization_obj)
                except:
                    send_organization_email_activation(request, organization_obj)
            if contacts and contacts != '':
                if isinstance(contacts, str):
                    contacts = json.loads(contacts)
                for cont in contacts:
                    cont.update({"organization": organization_obj.id})
                contact_serializer = OrganizationContactAddSerializer(data=contacts, many=True,
                                                                      context={'request': request})
                if contact_serializer.is_valid(raise_exception=True):
                    contact_serializer.create(validated_data=contacts)
                    data['contacts'] = contact_serializer.data
            return Response(data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class OrganizationDetailAPIView(RetrieveAPIView):
    serializer_class = OrganizationDetailSerializer
    permission_classes = [IsAuthenticated]
    queryset = OrganizationProfile.objects.all()
    lookup_field = 'pk'


class SearchOrganizationAPIView(ListAPIView):
    serializer_class = OrganizationListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        search_query = self.request.query_params.get('search_query')
        if search_query.lower() == 'all':
            qs = OrganizationProfile.objects.all()
        else:
            qs = OrganizationProfile.objects.filter(Q(organization_name__icontains=search_query) | Q(pro_code=search_query))
        return qs


class OrganizationContactAddView(CreateAPIView):
    serializer_class = OrganizationContactAddSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = OrganizationContactAddSerializer(data=data, context={'request': request}, many=True)
        if serializer.is_valid(raise_exception=True):
            serializer.create(validated_data=data)
            return Response(data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class OrganizationContactListAPIView(ListAPIView):
    serializer_class = OrganizationContactListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org_id = self.request.query_params.get('OrgId')
        if org_id:
            return OrganizationContact.objects.filter(user=self.request.user, organization_id=org_id).order_by('id')
        return OrganizationContact.objects.filter(user=self.request.user).order_by('id')


class CheckProCodeAPIView(CreateAPIView):
    serializer_class = CheckProCodeSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = CheckProCodeSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            return Response(serializer.data, status=HTTP_200_OK)
        else:
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class OrganizationTypeListAPIView(ListAPIView):
    serializer_class = OrganizationTypeSerializer
    queryset = OrganizationType.objects.all()
    permission_classes = [IsAuthenticated]


class OrganizationListAPIView(ListAPIView):
    """
    To list all the organizations
    """
    serializer_class = OrganizationListForLoginSerializer
    queryset = OrganizationProfile.objects.all().order_by('-created_at')
    permission_classes = [AllowAny]


class OrganizationContactDetailUpdateDeleteAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = OrganizationContactDetailUpdateDeleteSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return OrganizationContact.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        qs = UserOrganization.objects.filter(user=instance.user, organization=instance.organization)
        if qs.exists():
            qs.delete()
        instance.delete()


class AddressCreateAPIView(CreateAPIView):
    """
    Use this endpoint for CRUD operations of organization address
    """
    serializer_class = OrganizationAddAddressSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class AddressRetrieveUpdateDeleteAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = OrganizationAddAddressSerializer
    queryset = OrganizationAddress.objects.all()
    lookup_field = 'pk'
    permission_classes = [IsAuthenticated]


class OrganizationAddressListAPIView(ListAPIView):
    serializer_class = OrganizationAddressListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org_id = self.request.query_params.get('OrgId', None)
        return OrganizationAddress.objects.filter(organization_id=org_id)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if queryset:
            org_id = self.request.query_params.get('OrgId', None)
            if org_id:
                serializer = self.get_serializer(queryset[0])
        else:
            serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class OrganizationFloorsAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = OrganizationFloorsSerializer
    queryset = OrganizationFloors.objects.all()
    permission_classes = [IsAuthenticated]


class OrganizationFloorsListCreateAPIView(ListCreateAPIView):
    serializer_class = OrganizationFloorsSerializer
    queryset = OrganizationFloors.objects.all()
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = OrganizationFloorsSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            floor = request.data.get("floor_number", None)
            organization = request.data.get("organization", None)
            if OrganizationFloors.objects.filter(floor_number=floor, organization=organization).exists():
                return Response("This floor number has already exists with the organization",
                                status=HTTP_400_BAD_REQUEST)
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class OrganizationFloorDeleteAPIView(ListAPIView):
    """
    API to delete floors which already exists than the given count.
    :param OrgId : Id of organization,
    :param Floors : Count of total floors
    """
    serializer_class = OrganizationFloorsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org_id = self.request.query_params.get('OrgId', None)
        floors = self.request.query_params.get('Floors', None)
        OrganizationFloors.objects.filter(organization__id=org_id, floor_number__gt=floors).delete()
        return OrganizationFloors.objects.filter(organization__id=org_id)


class OrganizationFloorsListAPIView(ListAPIView):
    serializer_class = OrganizationFloorsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org_id = self.request.query_params.get('OrgId', None)
        floor_status = self.request.query_params.get('FloorStatus', None)
        if floor_status:
            return OrganizationFloors.objects.filter(organization__id=org_id, is_active=True).order_by('floor_number')
        else:
            return OrganizationFloors.objects.filter(organization__id=org_id).order_by('floor_number')


class UserOrganizationCreateAPIView(CreateAPIView):
    serializer_class = UserOrganizationCreateSerializer
    queryset = UserOrganization.objects.all()
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class OrganizationEmailActivationAPIView(CreateAPIView):
    serializer_class = OrganizationEmailActivationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        uid = request.data.get("uid", None)
        try:
            org_obj = OrganizationProfile.objects.get(id=uid)
            org_obj.is_email_verified = True
            org_obj.save()
            return Response("organization email successfully verified", status=HTTP_200_OK)
        except:
            return Response("No organization exists related to this email", status=HTTP_400_BAD_REQUEST)


class OrganizationGeoFenceListAPIView(ListAPIView):
    serializer_class = OrganizationGeoFenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org_id = self.request.query_params.get('OrgId', None)
        return OrganizationGeoFence.objects.filter(organization_id=org_id)


class OrganizationGeoFenceCreateAPIView(CreateAPIView):
    serializer_class = OrganizationGeoFenceSerializer
    permission_classes = [IsAuthenticated]
    queryset = OrganizationGeoFence.objects.all()


class OrganizationRetrieveUpdateDeleteAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = OrganizationGeoFenceSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    queryset = OrganizationGeoFence.objects.all()


class ZoneCCTVCreateAPIView(CreateAPIView):
    serializer_class = ZoneCCTVSerializer
    permission_classes = [IsAuthenticated]
    queryset = ZoneCCTV.objects.all()


class ZoneCCTVRetrieveUpdateDeleteAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = ZoneCCTVSerializer
    permission_classes = [IsAuthenticated]
    queryset = ZoneCCTV.objects.all()


class OrganizationZoneCCTVListAPIView(ListAPIView):
    serializer_class = ZoneCCTVGetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org_id = self.request.query_params.get('OrgId', None)
        if org_id:
            objs = ZoneCCTV.objects.filter(zone__organization_id=org_id)
            return objs
        return None


class OrganizationZoneCTVListAPIView(ListAPIView):
    """
    To get the CCTV details based on organization and zone data
    """
    serializer_class = ZoneCCTVGetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org_id = self.request.query_params.get('OrgId', None)
        zone_id = self.request.query_params.get('ZoneId', None)
        if org_id:
            objs = ZoneCCTV.objects.filter(zone__organization_id=org_id, zone__id=zone_id)
            return objs
        return None


class ZoneCCTVDeleteAPIView(CreateAPIView):
    serializer_class = ZoneCCTVDeleteSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        monitor_id = request.data.get('monitor_id', None)
        serializer = ZoneCCTVDeleteSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            ZoneCCTV.objects.filter(monitor_id=monitor_id).delete()
            return Response({'status': 'deleted'}, status=HTTP_200_OK)
        else:
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class DeleteZoneCCTVAPIView(CreateAPIView):
    serializer_class = ZoneCCTVDeleteSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        monitor_id = request.data.get('cctv_id', None)
        serializer = ZoneCCTVDeleteSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            ZoneCCTV.objects.filter(monitor_id=monitor_id).delete()
            return Response({'status': 'deleted'}, status=HTTP_200_OK)
        else:
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ZoneCCTVDetailsAPIView(CreateAPIView):
    serializer_class = ZoneCCTVDeleteSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        monitor_id = request.data.get('monitor_id', None)
        serializer = ZoneCCTVDeleteSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            cctc_obj = ZoneCCTV.objects.filter(monitor_id=monitor_id).first()
            data = ZoneCCTVSerializer(cctc_obj).data
            return Response(data, status=HTTP_200_OK)
        else:
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)



class ZoneDocumentCreateAPIView(CreateAPIView):
    serializer_class = ZoneDocumentSerializer
    permission_classes = [IsAuthenticated]
    queryset = ZoneDocument.objects.all()


class ZoneDocumentRetrieveUpdateDeleteAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = ZoneDocumentSerializer
    permission_classes = [IsAuthenticated]
    queryset = ZoneDocument.objects.all()


class ZoneCreateAPIView(ListCreateAPIView):
    serializer_class = ZoneSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Zone.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ZoneListAPIView(ListAPIView):
    """
    Get list of zones associated with organization
    """
    serializer_class = ZoneSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org_id = self.request.query_params.get('OrgId', None)
        return Zone.objects.filter(organization_id=org_id)


class ZoneDeleteAPIView(ListAPIView):
    serializer_class = ZoneSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org_id = self.request.query_params.get('OrgId', None)
        Zone.objects.filter(organization_id=org_id).delete()
        return Zone.objects.filter(organization_id=org_id)


class ZoneRetrieveUpdateDeleteAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = ZoneSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Zone.objects.filter(user=self.request.user)


class GetOrganizationByProCodeAPIView(CreateAPIView):
    serializer_class = GetOrganizationByProCodeSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = GetOrganizationByProCodeSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            return Response(serializer.data, status=HTTP_200_OK)
        else:
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class CreateZoneFloorsAPIView(CreateAPIView):
    """
    APIView to create floors detail for each floor
    """
    serializer_class = ZoneFloorSerializer
    permission_classes = [IsAuthenticated]
    queryset = ZoneFloor.objects.all()


class ZoneFloorRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve/Update/Destroy View for ZoneFloors
    """
    serializer_class = ZoneFloorSerializer
    permission_classes = [IsAuthenticated]
    queryset = ZoneFloor.objects.all()


class GetZoneFloorListAPIView(ListAPIView):
    """
    Get list of zone floors by zone id and Floor Id
    :param ZoneId - Id of zone
    :param FloorId - Id of organization floor
    """
    serializer_class = ZoneFloorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        zone_id = self.request.query_params.get('ZoneId', None)
        floor_id = self.request.query_params.get('FloorId', None)
        if zone_id and floor_id:
            return ZoneFloor.objects.filter(organization_zone__id=zone_id, floor__id=floor_id)
        return ZoneFloor.objects.filter(organization_zone__id=zone_id, floor=None)


class FindElevationAPIView(CreateAPIView):
    serializer_class = FindElevationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = FindElevationSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class OrganizationMessageListCreateAPIView(ListCreateAPIView):
    serializer_class = OrganizationMessageSerializer
    queryset = OrganizationMessage.objects.all()
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = OrganizationMessageSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            ser = serializer.save()
            organization_user = UserOrganization.objects.filter(organization=ser.organization)
            for user in organization_user:
                qs = FCMDevice.objects.filter(user=user.user)
                if qs.exists():
                    fcm_obj = qs.first()
                    data = {
                        "type": "organization-message",
                        "organization-message-id": ser.id
                    }
                    message = "%s organization is sent a  new message" % (
                        ser.organization.organization_name)
                    title = "Organization Messages"
                    if user.is_muted == False:
                        send_push_notification.delay(fcm_obj.id, title, message, data)
                        histroy = NotificationHistory(user=user.user, requested_user=request.user,
                                                      attribute=data,
                                                      notification_type="organization-message", message=message,
                                                      title=title)
                        histroy.save()
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

class GetOrganizationMessageAPIView(RetrieveAPIView):
    serializer_class = GetOrganizationMessageSerializer
    lookup_field = 'id'
    queryset = OrganizationMessage.objects.all()
    permission_classes = [IsAuthenticated]


class UpdateOrganizationMuteAPIView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MuteOrganisationSerializer

    def get_object(self):
        organisation_id = self.kwargs["organisation_id"]
        organisation = get_object_or_404(OrganizationProfile.objects.all(), pk=organisation_id)
        return UserOrganization.objects.get(user=self.request.user, organization=organisation)


class UpdateOrganizationUserInfoAPIView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserOrganisationInfoSerializer

    def get_object(self):
        organisation_id = self.kwargs["organisation_id"]
        organisation = get_object_or_404(OrganizationProfile.objects.all(), pk=organisation_id)
        return UserOrganization.objects.get(user=self.request.user, organization=organisation)


class UnsubscribeOrganizationAPIView(DestroyAPIView):
    """
    Delete organization instance
    """

    permission_classes = [IsAuthenticated]
    serializer_class = MuteOrganisationSerializer

    def get_object(self):
        organisation_id = self.kwargs["organisation_id"]
        organization = get_object_or_404(OrganizationProfile.objects.all(), pk=organisation_id)
        organisation = get_object_or_404(UserOrganization.objects.all(), organization=organization, user=self.request.user)
        return organisation