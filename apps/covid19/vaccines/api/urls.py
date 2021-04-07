from django.urls import path

from apps.covid19.vaccines.api.views import VaccineCreateAPIView, UpdateVaccineDetails, VaccineDeleteView, \
    DoseListAPIView, \
    ManufacturerListAPIView

urlpatterns = [

    path('add-vaccines/', VaccineCreateAPIView.as_view(), name='vaccine_list_view'),
    path("user-vaccines/<int:vaccine_id>/update/", UpdateVaccineDetails.as_view(), name="update_user_vaccine"),
    path("<int:vaccine_id>/delete/", VaccineDeleteView.as_view(), name="delete_user_vaccine"),
    path('list-doses/', DoseListAPIView.as_view(), name='dose_list_view'),
    path('list-manufacturers/', ManufacturerListAPIView.as_view(), name='manufacturer_list_view'),
]
