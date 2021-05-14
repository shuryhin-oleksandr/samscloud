from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ParentOrganizationProfileCreateAPIView,
    OrganizationUpdateAPIView,
    OrganizationDetailAPIView,
    UserOrganizationListAPIView,
    SearchOrganizationAPIView,
    OrganizationContactAddView,
    CheckProCodeAPIView,
    OrganizationTypeListAPIView,
    OrganizationContactListAPIView,
    OrganizationContactDetailUpdateDeleteAPIView,
    AddressCreateAPIView,
    AddressRetrieveUpdateDeleteAPIView,
    OrganizationFloorsAPIView,
    UserOrganizationCreateAPIView,
    OrganizationGeoFenceCreateAPIView,
    OrganizationRetrieveUpdateDeleteAPIView,
    ZoneCCTVCreateAPIView,
    ZoneCCTVRetrieveUpdateDeleteAPIView,
    ZoneDocumentCreateAPIView,
    ZoneDocumentRetrieveUpdateDeleteAPIView,
    ZoneCreateAPIView,
    ZoneRetrieveUpdateDeleteAPIView,
    OrganizationEmailActivationAPIView,
    GetOrganizationByProCodeAPIView,
    OrganizationFloorsListCreateAPIView,
    OrganizationGeoFenceListAPIView,
    OrganizationAddressListAPIView,
    CreateZoneFloorsAPIView,
    ZoneFloorRetrieveUpdateDestroyAPIView,
    OrganizationFloorsListAPIView,
    ZoneListAPIView,
    GetZoneFloorListAPIView,
    OrganizationFloorDeleteAPIView,
    ZoneDeleteAPIView,
    FindElevationAPIView,
    OrganizationZoneCCTVListAPIView,
    ZoneCCTVDeleteAPIView,
    ZoneCCTVDetailsAPIView,
    OrganizationListAPIView,
    OrganizationZoneCTVListAPIView, OrganizationMessageListCreateAPIView, GetOrganizationMessageAPIView,
    UpdateOrganizationMuteAPIView, UnsubscribeOrganizationAPIView, UpdateOrganizationUserInfoAPIView
)


urlpatterns = [
    # Organization
    path('', UserOrganizationListAPIView.as_view(), name='list'),
    path('register/', ParentOrganizationProfileCreateAPIView.as_view(), name='register'),
    path('<int:pk>/update/', OrganizationUpdateAPIView.as_view(), name='update'),
    path('<int:pk>/detail/', OrganizationDetailAPIView.as_view(), name='detail'),
    path('search-organization/', SearchOrganizationAPIView.as_view(), name='search-organization'),
    path('add-organization-contacts/', OrganizationContactAddView.as_view(), name='add-contact'),
    path('get-organization-type/', OrganizationTypeListAPIView.as_view(), name='get-organization-type'),
    path('organization-list/', OrganizationListAPIView.as_view(), name='organization-list'),

    # organization message
    path('create-organization-message/', OrganizationMessageListCreateAPIView.as_view(), name='create-organization-message'),
    path('get-organization-message/<int:id>', GetOrganizationMessageAPIView.as_view(), name='get-organization-message'),
    path('update-organization-mute/<int:organisation_id>', UpdateOrganizationMuteAPIView.as_view(), name='update-organization-mute'),
    path('update-organization-user-info/<int:organisation_id>', UpdateOrganizationUserInfoAPIView.as_view(),
         name='update-organization-user-info'),
    path('unsubscribe-organization/<int:organisation_id>', UnsubscribeOrganizationAPIView.as_view(),
         name='unsubscribe-organization'),

    # Organization Procode
    path('check-pro-code/', CheckProCodeAPIView.as_view(), name='check-pro-code'),
    path('get-organization-by-pro-code/', GetOrganizationByProCodeAPIView.as_view(),
         name='get-organization-by-pro-code'),

    # Organization contacts
    path('get-organization-contacts/', OrganizationContactListAPIView.as_view(), name='get-organization-contact'),

    path('<int:pk>/organization-contacts-detail-update-delete/', OrganizationContactDetailUpdateDeleteAPIView.as_view(),
         name='organization-contacts-detail-update-delete'),
    path('create-user-organization/', UserOrganizationCreateAPIView.as_view(), name='create-user-organization'),
    path('activate-organization-email/', OrganizationEmailActivationAPIView.as_view(),
         name='activate-organization-email'),

    # Organization Address
    path('address/', AddressCreateAPIView.as_view(), name='address'),
    path('address/<int:pk>/', AddressRetrieveUpdateDeleteAPIView.as_view(), name='address'),
    path('address-list/', OrganizationAddressListAPIView.as_view(), name='address-list'),

    # Organization floors
    path('floors/<int:pk>/', OrganizationFloorsAPIView.as_view(), name='floors'),
    path('floors/', OrganizationFloorsListCreateAPIView.as_view(), name='floors-create'),
    path('floors-list/', OrganizationFloorsListAPIView.as_view(), name='floors-list'),
    path('delete-existing-floors/', OrganizationFloorDeleteAPIView.as_view(), name='delete-floors'),
    path('find-elevation/', FindElevationAPIView.as_view(), name='find-elevation'),

    # Geofence
    path('add-geo-fence/', OrganizationGeoFenceCreateAPIView.as_view(), name='add-geo-fence'),
    path('get-organization-geo-fence/', OrganizationGeoFenceListAPIView.as_view(), name='get-organization-geo-fence'),
    path('<int:pk>/geo-fence/', OrganizationRetrieveUpdateDeleteAPIView.as_view(), name='geo-fence'),

    # Zone CCTV
    path('zone/add-cctv/', ZoneCCTVCreateAPIView.as_view(), name='add-cctv'),
    path('<int:pk>/zone-cctv/', ZoneCCTVRetrieveUpdateDeleteAPIView.as_view(), name='cctv-get-update-delete'),
    path('organization-cctv-list/', OrganizationZoneCCTVListAPIView.as_view(), name='organization-cctv-list'),
    path('cctv-delete/', ZoneCCTVDeleteAPIView.as_view(), name='cctv-delete'),
    path('cctv-details/', ZoneCCTVDetailsAPIView.as_view(), name='cctv-details'),
    path('organization-zone-cctv-list/', OrganizationZoneCTVListAPIView.as_view(), name='organization-zone-cctv-list'),
    # path('delete-zone-cctv/', DeleteZoneCCTVAPIView.as_view(), name='delete-zone-cctv'),

    # Zone document
    path('zone/add-document/', ZoneDocumentCreateAPIView.as_view(), name='add-document'),
    path('<int:pk>/zone-document/', ZoneDocumentRetrieveUpdateDeleteAPIView.as_view(),
         name='document-get-update-delete'),

    # Zones
    path('zones/', ZoneCreateAPIView.as_view(), name='zones'),
    path('get-organization-zones/', ZoneListAPIView.as_view(), name='get-organization-zones'),
    path('<int:pk>/zone/', ZoneRetrieveUpdateDeleteAPIView.as_view(), name='zone-get-update-delete'),
    path('zone-delete/', ZoneDeleteAPIView.as_view(), name='zone-delete'),

    # Zone floor
    path('create-zone-floor/', CreateZoneFloorsAPIView.as_view(), name='zone-floor-create'),
    path('get-zone-items-list-by-zone-floor/', GetZoneFloorListAPIView.as_view(),
         name='get-zone-items-list-by-zone-floor/'),
    path('<int:pk>/zone-floor/', ZoneFloorRetrieveUpdateDestroyAPIView.as_view(), name='zone-floor-get-update-delete'),
]
