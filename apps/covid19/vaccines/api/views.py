import datetime
import json
import re

from django.db.models import Sum, Count
from django.shortcuts import render

# Create your views here.
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView, DestroyAPIView, get_object_or_404, \
    ListAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.covid19.covid_accounts.models import UserReport, Lastupdated
from apps.covid19.location.models import UserLocations, GlobalLocations, AssistanceLocations
from apps.covid19.location.api.serializers import UserLocationSerializer, GlobalLocationListSerializer, \
    GlobalLocationDetailSerializer, AssistanceLocationDetailsSerializer

from apps.covid19.vaccines.models import UserVaccine, Dose, Manufacturer
from apps.covid19.vaccines.api.serializers import UserVaccineSerializer, DoseSerializer, ManufacturerSerializer, \
    UserVaccineUpdateSerializer


class VaccineCreateAPIView(ListCreateAPIView):
    """
    User Vaccine Detail Create APIView
    """
    serializer_class = UserVaccineSerializer
    queryset = UserVaccine.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return UserVaccine.objects.filter(user=user).order_by('-vaccinated_date')

    def create(self, request, *args, **kwargs):
        data = request.data
        user = self.request.user
        user.last_updated = timezone.now()
        user.is_vaccinated = True
        user.save()
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        report = UserReport.objects.filter(user=self.request.user).last()
        serializer = UserVaccineSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            manufacturer = Manufacturer.objects.get(id=self.request.data['manufacturer'])
            dosage = Dose.objects.get(id=self.request.data['dosage'])
            serializer.save(user=self.request.user, manufacturer=manufacturer, dosage=dosage)
            data = serializer.data
            if report:
                report.is_vaccinated = True
                report.vaccine_id = data['id']
                report.save()
            headers = self.get_success_headers(serializer.data)
            return Response(data, status=status.HTTP_201_CREATED, headers=headers)


class UpdateVaccineDetails(RetrieveUpdateAPIView):
    """
    View to retrieve patch update vaccine details
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserVaccineUpdateSerializer

    def get_object(self):
        user = self.request.user
        user.last_updated = timezone.now()
        user.save()
        vaccine_id = self.kwargs["vaccine_id"]
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        return UserVaccine.objects.get(id=vaccine_id)


class VaccineDeleteView(DestroyAPIView):
    """
    Delete vaccine instance
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserVaccineUpdateSerializer

    def get_object(self):
        user = self.request.user
        user.last_updated = timezone.now()
        user.save()
        report = UserReport.objects.filter(user=self.request.user).last()
        vaccine_id = self.kwargs["vaccine_id"]
        vaccine = get_object_or_404(UserVaccine.objects.all(), pk=vaccine_id)
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        return vaccine


class DoseListAPIView(ListAPIView):
    """
    List Doses
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DoseSerializer

    def get_queryset(self):
        return Dose.objects.all()


class ManufacturerListAPIView(ListAPIView):
    """
    List Manufacturers
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ManufacturerSerializer

    def get_queryset(self):
        return Manufacturer.objects.all()
