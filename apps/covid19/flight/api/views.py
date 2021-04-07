from datetime import timedelta

from django.shortcuts import render

# Create your views here.
from django.utils import timezone
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveUpdateAPIView, DestroyAPIView, \
    get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import User
from apps.covid19.covid_accounts.models import UserReport, Lastupdated
from apps.covid19.flight.models import Flight, FlightDetails, Questions, UserAnswers
from apps.covid19.flight.api.serializers import FlightSerializer, FlightDetailsSerializer, \
    FlightDetailsReadonlySerializer, \
    QuestionSerializer, UserAnswerSerializer


class FlightListAPIView(ListAPIView):
    """
    List Flight Carriers
    """

    permission_classes = [IsAuthenticated]
    serializer_class = FlightSerializer

    def get_queryset(self):
        return Flight.objects.all()


class FlightDetailCreateAPIView(ListCreateAPIView):
    """
    User Flight Detail Create APIView
    """
    serializer_class = FlightDetailsSerializer
    queryset = FlightDetails.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return FlightDetails.objects.filter(user=user)

    def list(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = FlightDetailsReadonlySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = FlightDetailsReadonlySerializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        report = UserReport.objects.filter(user=self.request.user).last()
        user = self.request.user
        user.last_updated = timezone.now()
        user.save()
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        if report and report.test_result == "Positive":
            if report.data_started and report.data_started - timedelta(days=15) <= serializer.validated_data[
                'date_journey'] <= report.data_started + timedelta(days=15):
                effect_flight_user = FlightDetails.objects.filter(
                    date_journey=serializer.validated_data['date_journey'], flight=serializer.validated_data['flight'],
                    flight_no=serializer.validated_data['flight_no'])
                if effect_flight_user:
                    for effect in effect_flight_user:
                        try:
                            flight_user = User.objects.get(id=effect.user.id)
                            flight_user.flight_exposure += 1
                            flight_user.save()
                        except:
                            pass
                user.risk_level = True
                user.save()
                serializer.save(user=self.request.user, is_infected=True)
        else:
            effect_flight_user = FlightDetails.objects.filter(date_journey=serializer.validated_data['date_journey'],
                                                              flight=serializer.validated_data['flight'],
                                                              flight_no=serializer.validated_data['flight_no'],
                                                              is_infected=True)
            if effect_flight_user:
                user.flight_exposure += 1
                user.risk_level = True
                user.save()
                serializer.save(user=self.request.user, is_infected=True)

        serializer.save(user=self.request.user)


class UpdateFlightDetails(RetrieveUpdateAPIView):
    """
    View to retrieve patch update flight details
    """
    permission_classes = [IsAuthenticated]
    serializer_class = FlightDetailsSerializer

    def get_object(self):
        user = self.request.user
        user.last_updated = timezone.now()
        user.save()
        flightdetail_id = self.kwargs["flightdetail_id"]
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        return FlightDetails.objects.get(id=flightdetail_id)


class FlightDetailDeleteView(DestroyAPIView):
    """
    Delete flight detail instance
    """

    permission_classes = [IsAuthenticated]
    serializer_class = FlightDetailsSerializer

    def get_object(self):
        user = self.request.user
        user.last_updated = timezone.now()
        user.save()
        flightdetail_id = self.kwargs["flightdetail_id"]
        try:
            report = UserReport.objects.filter(user=self.request.user).last()
            flight = FlightDetails.objects.get(id=flightdetail_id)
            if report and report.test_result == "Positive":
                effect_flight = FlightDetails.objects.filter(date_journey=flight.date_journey,
                                                             flight=flight.flight,
                                                             flight_no=flight.flight_no)
                if effect_flight:
                    for effect in effect_flight:
                        try:
                            flight_user = User.objects.get(id=effect.user.id)
                            flight_user.flight_exposure -= 1
                            flight_user.save()
                        except:
                            pass
                user.risk_level = False
                user.save()
            else:
                effect_flight_user = FlightDetails.objects.filter(date_journey=flight.date_journey,
                                                                  flight=flight.flight,
                                                                  flight_no=flight.flight_no, is_infected=True)
                if effect_flight_user:
                    user.flight_exposure -= 1
                    user.risk_level = False
                    user.save()
        except:
            pass
        details = get_object_or_404(FlightDetails.objects.all(), pk=flightdetail_id)
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        return details


class QuestionfirstListAPIView(ListAPIView):
    """
    List question first section
    """

    permission_classes = [IsAuthenticated]
    serializer_class = QuestionSerializer

    def get_queryset(self):
        return Questions.objects.filter(type='GENERAL')


class QuestionsecondListAPIView(ListAPIView):
    """
    List question second section
    """

    permission_classes = [IsAuthenticated]
    serializer_class = QuestionSerializer

    def get_queryset(self):
        return Questions.objects.filter(type='ADVANCED')


class UseranswerListCreateAPIView(ListCreateAPIView):
    """
    User Question Answer List Create APIView
    """
    serializer_class = UserAnswerSerializer
    queryset = UserAnswers.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return UserAnswers.objects.filter(user=user)

    def perform_create(self, serializer):
        user = self.request.user
        user.last_updated = timezone.now()
        user.save()
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        serializer.save(user=self.request.user)
