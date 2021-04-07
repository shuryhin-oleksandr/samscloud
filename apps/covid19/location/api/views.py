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
    GlobalLocationDetailSerializer, AssistanceLocationDetailsSerializer, UserLocationUpdateSerializer


class LocationCreateAPIView(ListCreateAPIView):
    """
    User Location Detail Create APIView
    """
    serializer_class = UserLocationSerializer
    queryset = UserLocations.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return UserLocations.objects.filter(user=user, is_hidden=False).order_by('-location_date', '-to_time')

    def create(self, request, *args, **kwargs):
        report = UserReport.objects.filter(user=request.user).last()
        user = request.user
        user.last_updated = timezone.now()
        user.save()
        if 'data' not in self.request.data:
            serializer = UserLocationSerializer(data=request.data, context={'request': request, 'report': report})
            if serializer.is_valid(raise_exception=True):
                serializer.save()
        else:
            serializer = UserLocationSerializer(data=request.data["data"],
                                                context={'request': request, 'report': report},
                                                many=True)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class UpdateLocationDetails(RetrieveUpdateAPIView):
    """
    View to retrieve patch update location details
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserLocationUpdateSerializer

    def get_object(self):
        user = self.request.user
        user.last_updated = timezone.now()
        user.save()
        location_id = self.kwargs["location_id"]
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        return UserLocations.objects.get(id=location_id)


class LocationDeleteView(DestroyAPIView):
    """
    Delete location instance
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserLocationSerializer

    def get_object(self):
        user = self.request.user
        user.last_updated = timezone.now()
        user.save()
        report = UserReport.objects.filter(user=self.request.user).last()
        location_id = self.kwargs["location_id"]
        try:
            location = UserLocations.objects.get(id=location_id)
            if report and report.test_result == "Positive":
                delta = datetime.timedelta(hours=3)
                start = (datetime.datetime.combine(datetime.date(9999, 1, 1),
                                                   location.from_time) - delta).time()
                end = (datetime.datetime.combine(datetime.date(9999, 1, 1),
                                                 location.to_time) + delta).time()
                effect_location_user = UserLocations.objects.filter(
                    location_date=location.location_date,
                    location=location.location,
                    from_time__gte=start,
                    to_time__lte=end)
                if effect_location_user:
                    for effect in effect_location_user:
                        try:
                            if user != effect.user:
                                location_user = User.objects.get(id=effect.user.id)
                                location_user.location_exposure -= 1
                                location_user.save()
                        except:
                            pass
            else:
                infected_location = UserLocations.objects.filter(
                    location_date=location.location_date,
                    location=location.location, is_infected=True)
                infected_data = []
                if infected_location:
                    for infect in infected_location:
                        delta = datetime.timedelta(hours=3)
                        start = (datetime.datetime.combine(datetime.date(9999, 1, 1),
                                                           infect.from_time) - delta).time()
                        end = (datetime.datetime.combine(datetime.date(9999, 1, 1),
                                                         infect.to_time) + delta).time()

                        if start < end:
                            if location.from_time >= start and location.from_time <= end:
                                infected_data.append(infect)
                                # infect.user.location_exposure += 1

                        else:  # Over midnight
                            if location.from_time >= start or location.from_time <= end:
                                infected_data.append(infect)

                if infected_data:
                    user.location_exposure -= 1
                    user.save()
        except:
            pass
        location = get_object_or_404(UserLocations.objects.all(), pk=location_id)
        last_updated = Lastupdated(updated_time=timezone.now())
        last_updated.save()
        return location


class GlobaldataListAPIView(APIView):
    """
    List global country wise details
    """

    permission_classes = [AllowAny]

    def get(self, request, country, format=None):
        """
        Return a list of country details.
        """

        # l = GlobalLocations.objects.filter(Country_Region=country).values('Province_State').annotate(Sum('Confirmed')).order_by('-Confirmed')
        province = GlobalLocations.objects.filter(Country_Region__iexact=country).values_list('Province_State',
                                                                                              flat=True).distinct()
        # a = GlobalLocations.objects.filter(Province_State__in=province, Country_Region=country).aggregate(confiremed_sum=Sum('Confirmed')).order_by('confiremed_sum')
        # a = GlobalLocations.objects.filter(Province_State__in=province).aggregate(confiremed_sum=Sum('Confirmed').order_by('confiremed_sum'))
        data = []
        for i in province:
            province_lat = GlobalLocations.objects.filter(Province_State__iexact=i,
                                                          Country_Region__iexact=country).first()
            province_count = GlobalLocations.objects.filter(Province_State__iexact=i,
                                                            Country_Region__iexact=country).aggregate(Sum('Confirmed'),
                                                                                                      Sum('Deaths'),
                                                                                                      Sum('Recovered'),
                                                                                                      Sum('Active'))
            province_count.update(
                {"Province_State": i, "Country_Region": country, "Lat": province_lat.Lat, "Long": province_lat.Long})
            data.append(province_count)
        newlist = sorted(data, reverse=True, key=lambda k: k['Confirmed__sum'] if k['Confirmed__sum'] else 0)
        return Response(newlist)


class GlobalCountryListAPIView(APIView):
    """
   List global covid country's
   """
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        """
        Return a list of countrys.
        """

        country = GlobalLocations.objects.distinct('Country_Region').values()
        data = []
        total_count = GlobalLocations.objects.all().aggregate(Total_confirmed=Sum('Confirmed'),
                                                              Total_Deaths=Sum('Deaths'),
                                                              Total_Recovered=Sum('Recovered'),
                                                              Total_Active=Sum('Active'))
        #
        for con in country:
            country_count = GlobalLocations.objects.filter(Country_Region__iexact=con.get("Country_Region")).aggregate(
                Sum('Confirmed'), Sum('Deaths'),
                Sum('Recovered'), Sum('Active'))
            country_count.update(
                {"Country_Region": con.get("Country_Region"), "Lat": con.get("Lat"), "Long": con.get("Long")})
            region = GlobalLocations.objects.filter(Country_Region=con.get("Country_Region"))
            country_count.update({"province_state": False})
            for re in region:
                if re.Province_State and country_count.get('province_state') == False:
                    country_count.update({"province_state": True})
            data.append(country_count)
        newlist = sorted(data, reverse=True, key=lambda k: k['Confirmed__sum'] if k['Confirmed__sum'] else 0)
        newlist.insert(0, total_count)
        return Response(newlist)


class GlobalCountryStatusListAPIView(APIView):
    """
    List global country status
    """

    permission_classes = [AllowAny]

    def get(self, request, country, format=None):
        """
        Return a list of country status.
        """

        a = GlobalLocations.objects.filter(Country_Region__iexact=country).aggregate(Sum('Confirmed'), Sum('Deaths'),
                                                                                     Sum('Recovered'), Sum('Active'))
        return Response(a)


class GlobalCountryEffectsAPIView(APIView):
    """
    List global effects
    """

    permission_classes = [AllowAny]

    def get(self, request, format=None):
        """
        Return a list of global effects.
        """

        total_count = GlobalLocations.objects.all().aggregate(Total_confirmed=Sum('Confirmed'),
                                                              Total_Deaths=Sum('Deaths'),
                                                              Total_Recovered=Sum('Recovered'),
                                                              Total_Active=Sum('Active'))
        return Response(total_count)


class UsersLocationListAPIView(ListAPIView):
    """
    List users location wise details
    """

    permission_classes = [AllowAny]
    serializer_class = UserLocationSerializer

    def get_queryset(self):
        """
        Return a list of country or location details.
        """

        country = self.kwargs["country"]
        city = self.request.query_params.get('city', None)
        province = self.request.query_params.get('province', None)
        try:
            if city and province:
                location = UserLocations.objects.filter(Country_Region__iexact=country,
                                                        Province_State__iexact=province, City__iexact=city)
                report_locations = UserReport.objects.filter(user__country=country,
                                                             user__state=province, user__city=city)
            elif city or province:
                if city:
                    location = UserLocations.objects.filter(Country_Region__iexact=country, City__iexact=city)
                    report_locations = UserReport.objects.filter(user__country=country, user__city=city)
                else:
                    location = UserLocations.objects.filter(Country_Region__iexact=country,
                                                            Province_State__iexact=province)
                    report_locations = UserReport.objects.filter(user__country=country,
                                                                 user__state=province)
            else:
                location = UserLocations.objects.filter(Country_Region__iexact=country)
                report_locations = UserReport.objects.filter(user__country=country)
            if report_locations:
                newdict = {'self_report_count': report_locations.values_list('user').distinct().count()}
                newdict.update({"location": location})
                return newdict
            newdict = {'self_report_count': 0}
            newdict.update({"location": location})
            return newdict
        except UserLocations.DoesNotExist:
            return Response("Location does not exists", status=HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        if queryset:
            c = queryset['self_report_count']
            q = queryset['location']
            serializer = self.get_serializer(q, many=True)
            newdict = {'self_report_count': c}
            newdict.update({"location": serializer.data})
            return Response(newdict, status=status.HTTP_200_OK)
        return Response({}, status=HTTP_400_BAD_REQUEST)


class ZipCityDetailsListAPIView(ListAPIView):
    """
        List city wise details
        """

    permission_classes = [AllowAny]
    serializer_class = GlobalLocationDetailSerializer

    def get_queryset(self):
        """
        Return a list of city details.
        """
        country = self.kwargs["country"]
        city = self.request.query_params.get('city', None)
        province = self.kwargs["province"]
        try:
            if city:
                location = GlobalLocations.objects.filter(Country_Region__iexact=country,
                                                          Province_State__icontains=province, City__icontains=city)
            else:
                location = GlobalLocations.objects.filter(Country_Region__iexact=country,
                                                          Province_State__icontains=province)
        except GlobalLocations.DoesNotExist:
            pass
        return location


class GlobalJsonListAPIView(ListAPIView):
    """
        List all data in golbal location details
        """

    permission_classes = [AllowAny]
    serializer_class = GlobalLocationDetailSerializer

    def get_queryset(self):
        """
        Return a list of all location details.
        """
        return GlobalLocations.objects.all()


class ProvienceLabListAPIView(APIView):
    """
    List  provience wise labs
    """

    permission_classes = [AllowAny]

    def get(self, request, province, format=None):
        """
        Return a list of country details.
        """
        try:
            with open('labs/' + province + '.JSON') as f:
                data = json.load(f)
        except:
            data = {"status": "province doesn't have any labs"}
        return Response(data)


class AllLabListAPIView(APIView):
    """
    List  all  labs
    """

    permission_classes = [AllowAny]

    def get(self, request, format=None):
        """
        Return a list of labs details.
        """
        try:
            with open('labs/all.JSON') as f:
                data = json.load(f)
        except:
            data = {"status": "we doesn't have any lab details"}
        return Response(data)


class UnknownUserAddLocationView(APIView):
    """
    User Location Detail Create APIView
    """
    queryset = UserLocations.objects.all()
    permission_classes = [AllowAny]

    def post(self, request, format=None):
        infected_data = []
        if request.data:
            locations = request.data
            for data in locations:
                first_exposure_date = ''
                latest_exposure_date = ''
                counts = UserLocations.objects.filter(location=data.get("location")).count()
                if UserLocations.objects.filter(location=data.get("location"), is_infected=True):
                    first_exposure_date = UserLocations.objects.filter(location=data.get("location"),
                                                                       is_infected=True).earliest(
                        'location_date').location_date
                    latest_exposure_date = UserLocations.objects.filter(location=data.get("location"),
                                                                        is_infected=True).latest(
                        'location_date').location_date
                infected_location = UserLocations.objects.filter(location_date=data.get("location_date"),
                                                                 location=data.get("location"), is_infected=True)
                count = 0
                if infected_location:
                    for infect in infected_location:
                        delta = datetime.timedelta(hours=3)
                        start = (datetime.datetime.combine(datetime.date(9999, 1, 1),
                                                           infect.from_time) - delta).time()
                        end = (datetime.datetime.combine(datetime.date(9999, 1, 1),
                                                         infect.to_time) + delta).time()

                        data_time = datetime.datetime.strptime(data.get("from_time"), '%H:%M:%S').time()
                        if start < end:

                            if data_time >= start and data_time <= end:
                                count += 1

                        else:  # Over midnight
                            if data_time >= start or data_time <= end:
                                count += 1
                data.update({"location_count": counts, "location_infected_count": count,
                             "first_exposure_date": first_exposure_date, "latest_exposure_date": latest_exposure_date})
                infected_data.append(data)
            return Response(infected_data)
        return Response(infected_data)


class AssistanceLocationCreateAPIView(ListCreateAPIView):
    """
    Assistance location Detail Create APIView
    """
    serializer_class = AssistanceLocationDetailsSerializer
    queryset = AssistanceLocations.objects.all()
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AssistanceLocationListAPIView(APIView):
    """
    List assistance locations
    """

    permission_classes = [AllowAny]

    # serializer_class = AssistanceLocationDetailsSerializer
    # queryset = AssistanceLocations.objects.all()
    # def get(self, request, format=None):
    #     """
    #     Return a list of global effects.
    #     """
    #     data = []
    #     activity = ['Food Aid', 'Supplies', 'Financial Help', 'Test Center', 'Vaccine']
    #     newdict = {}
    #     for act in activity:
    #         filter_data = AssistanceLocations.objects.filter(activity=act).all()
    #         seralizer = AssistanceLocationDetailsSerializer(filter_data, many=True)
    #         newdict.update({act: seralizer.data})
    #     data.append(newdict)
    #     return Response(data)

    def get(self, request, format=None):
        """
        Return a list of labs details.
        """
        data = AssistanceLocations.objects.all()
        values = []
        for value in data:
            from_date = value.from_date
            to_date = value.to_date
            display_location = value.dispaly_location
            week = int(re.search(r'\d+', display_location).group())
            from_dt = from_date - datetime.timedelta(days=week * 7)
            date = datetime.date.today()
            if from_dt < date < to_date:
                values.append(value)
        seralizer = AssistanceLocationDetailsSerializer(values, many=True)
        return Response(seralizer.data)


class AssistanceDeleteAPIView(DestroyAPIView):
    """
    Delete assistance location instance
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AssistanceLocationDetailsSerializer

    def get_object(self):
        assistance_id = self.kwargs["assistance_id"]
        assistance = get_object_or_404(AssistanceLocations.objects.filter(user=self.request.user), pk=assistance_id)
        return assistance
