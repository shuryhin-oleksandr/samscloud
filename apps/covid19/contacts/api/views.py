import datetime

from django.shortcuts import render

# Create your views here.
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView, DestroyAPIView, get_object_or_404, \
    ListAPIView
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import User
from apps.covid19.covid_accounts.models import UserReport, Lastupdated
from apps.covid19.contacts.models import UserContacts, Disease, Symptoms, UserContactTagging
from apps.covid19.contacts.api.serializers import UserContactSerializer, DiseaseSerializer, SymptomsSerializer, \
    UserContactTaggingSerializer


class ContactCreateAPIView(ListCreateAPIView):
    """
    User Contact Create APIView
    """
    serializer_class = UserContactSerializer
    queryset = UserContacts.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return UserContacts.objects.filter(user=user)

    def create(self, request, *args, **kwargs):
        report = UserReport.objects.filter(user=self.request.user).last()
        user = self.request.user
        user.last_updated = timezone.now()
        user.save()
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        if 'data' not in self.request.data:
            serializer = UserContactSerializer(data=request.data, context={'request': request, 'report': report})
            if serializer.is_valid(raise_exception=True):
                serializer.save()
        else:
            serializer = UserContactSerializer(data=request.data["data"],
                                               context={'request': request, 'report': report},
                                               many=True)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ContactTaggingCreateAPIView(ListCreateAPIView):
    """
    User Contact Tagging Create APIView
    """
    serializer_class = UserContactTaggingSerializer
    queryset = UserContactTagging.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return UserContactTagging.objects.filter(user=user)

    def create(self, request, *args, **kwargs):
        report = UserReport.objects.filter(user=self.request.user).last()
        user = self.request.user
        user.last_updated = timezone.now()
        user.save()
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        if 'data' not in self.request.data:
            serializer = UserContactTaggingSerializer(data=request.data, context={'request': request, 'report': report})
            if serializer.is_valid(raise_exception=True):
                serializer.save()
        else:
            serializer = UserContactTaggingSerializer(data=request.data["data"],
                                                      context={'request': request, 'report': report},
                                                      many=True)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class UpdateContactDetails(RetrieveUpdateAPIView):
    """
    View to retrieve patch update contact details
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserContactSerializer

    def get_object(self):
        user = self.request.user
        user.last_updated = timezone.now()
        user.save()
        contact_id = self.kwargs["contact_id"]
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        return UserContacts.objects.get(id=contact_id)


class ContactsDeleteView(DestroyAPIView):
    """
    Delete contact instance
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserContactSerializer

    def get_object(self):
        user = self.request.user
        user.last_updated = timezone.now()
        user.save()
        contact_id = self.kwargs["contact_id"]
        report = UserReport.objects.filter(user=self.request.user).last()
        try:
            contact = UserContacts.objects.get(id=contact_id)
            if report and report.test_result == "Positive":
                try:
                    contact_user = User.objects.get(phone_number=contact.phone_number)
                    if user != contact_user:
                        contact_user.contact_exposure -= 1
                    contact_user.save()
                except:
                    pass
            else:
                effect_contact = UserContacts.objects.filter(phone_number=contact.phone_number,
                                                             date_contacted__range=[
                                                                 contact.date_contacted - datetime.timedelta(days=15),
                                                                 contact.date_contacted + datetime.timedelta(days=15)],
                                                             is_infected=True)
                if effect_contact:
                    user.risk_level = False
                    user.contact_exposure -= 1
                    user.save()
                else:
                    try:
                        contact_user = User.objects.get(phone_number=contact.phone_number)
                        if contact_user:
                            user.risk_level = True
                            user.contact_exposure += 1
                            user.save()
                    except:
                        pass
        except:
            pass
        contact = get_object_or_404(UserContacts.objects.all(), pk=contact_id)
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        return contact


class DiseaseListAPIView(ListAPIView):
    """
    List Diseases
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DiseaseSerializer

    def get_queryset(self):
        return Disease.objects.all()


class SymptomsListAPIView(ListAPIView):
    """
    List Symptoms
    """

    permission_classes = [IsAuthenticated]
    serializer_class = SymptomsSerializer

    def get_queryset(self):
        return Symptoms.objects.all()
