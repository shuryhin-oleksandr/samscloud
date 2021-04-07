from django.urls import path

from apps.covid19.location.api.views import LocationCreateAPIView, UpdateLocationDetails, LocationDeleteView, GlobaldataListAPIView, \
    GlobalCountryListAPIView, GlobalCountryStatusListAPIView, GlobalCountryEffectsAPIView, UsersLocationListAPIView, \
    ZipCityDetailsListAPIView, GlobalJsonListAPIView, ProvienceLabListAPIView, AllLabListAPIView, \
    UnknownUserAddLocationView, AssistanceLocationCreateAPIView, AssistanceLocationListAPIView, AssistanceDeleteAPIView

urlpatterns = [

    path('add-locations/', LocationCreateAPIView.as_view(), name='location_list_view'),
    path("user-locations/<int:location_id>/update/", UpdateLocationDetails.as_view(), name="update_user_locations"),
    path("<int:location_id>/delete/", LocationDeleteView.as_view(), name="delete_user_location"),
    path('global-country-details/<str:country>/', GlobaldataListAPIView.as_view(), name='global_countrydetails_view'),
    path('list_global-countrys/', GlobalCountryListAPIView.as_view(), name='global_listcountry_view'),
    path('global-effects/', GlobalCountryEffectsAPIView.as_view(), name='global_countryeffects_view'),
    path('global-country-status/<str:country>/', GlobalCountryStatusListAPIView.as_view(), name='global_countrystatus_view'),
    path('users-location-details/<str:country>/', UsersLocationListAPIView.as_view(), name='users_locationdetails_view'),
    path('city-details-zip/<str:country>/<str:province>/', ZipCityDetailsListAPIView.as_view(), name='zip_citydetails_view'),
    path('global-data-json/', GlobalJsonListAPIView.as_view(), name='global_data_json_view'),
    path('province-lab-locations/<str:province>/', ProvienceLabListAPIView.as_view(), name='provience_lablocations_view'),
    path('all-lab-locations/', AllLabListAPIView.as_view(), name='all_lablocations_view'),
    path('unknownuser_location_risk/', UnknownUserAddLocationView.as_view(), name='unknownuser_locations_view'),
    path('add-assistance-locations/', AssistanceLocationCreateAPIView.as_view(), name='assistance_location_list_view'),
    path('list-assistance-locations/', AssistanceLocationListAPIView.as_view(), name='assistance_location_filteredlist_view'),
    path("<int:assistance_id>/assistance/delete/", AssistanceDeleteAPIView.as_view(), name="delete_assistance_location"),
]