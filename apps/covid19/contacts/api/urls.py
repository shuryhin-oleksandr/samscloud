from django.urls import path

from apps.covid19.contacts.api.views import ContactCreateAPIView, UpdateContactDetails, ContactsDeleteView, \
    SymptomsListAPIView, \
    DiseaseListAPIView, ContactTaggingCreateAPIView

urlpatterns = [
    path('add-contact/', ContactCreateAPIView.as_view(), name='contact_list_create'),
    path('add-contact-tagging/', ContactTaggingCreateAPIView.as_view(), name='contact_tagging_list_create'),
    path("user-contact/<int:contact_id>/update/", UpdateContactDetails.as_view(), name="update_user_contact"),
    path("<int:contact_id>/delete/", ContactsDeleteView.as_view(), name="delete_user_contacts"),
    path('list-disease/', DiseaseListAPIView.as_view(), name='disease_list_view'),
    path('list-symptoms/', SymptomsListAPIView.as_view(), name='symptoms_list_view'),
]
