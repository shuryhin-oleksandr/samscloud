from django.db.models import Subquery, OuterRef, F, Q
from django.db.models.functions import Greatest
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import User
from apps.covid19.dashboard.filters import DashboardResultsFilter, DashboardChartGraphFilter
from apps.covid19.contacts.models import UserContacts
from apps.covid19.covid_accounts.models import UserTesting
from apps.covid19.dashboard.filters import DashboardChartGraphFilter
from apps.covid19.flight.models import FlightDetails
from apps.covid19.location.models import UserLocations
from apps.organization.models import OrganizationProfile


class DashboardGraphView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def _get_notified_without_testing_count(self, queryset, response_query):
        latest_test = Subquery(UserTesting.objects.filter(
            user_id=OuterRef("id"),
        ).order_by("-tested_date").values('tested_date')[:1])
        count = queryset.annotate(latest_test=latest_test).filter(
            (
                Q(user_testing__isnull=False) &
                Q(notificationhistoryuser__notification_type='high-risk-area') &
                (
                    Q(notificationhistoryuser__date_created__gte=F('latest_test')) &
                    response_query
                )
            )
        ).distinct().count()

        return count

    def _get_testing_block(self, queryset):
        negative = queryset.filter(user_testing__test_result='Negative').distinct().count()
        positive = queryset.filter(user_testing__test_result='Positive').distinct().count()

        queryset = queryset.exclude(user_vaccine__isnull=False)
        response_time = timezone.timedelta(days=15)
        no_response = self._get_notified_without_testing_count(
            queryset, Q(notificationhistoryuser__date_created__lte=timezone.now() - response_time))

        pending = self._get_notified_without_testing_count(
            queryset, Q(notificationhistoryuser__date_created__gte=timezone.now() - response_time))

        return negative, positive, no_response, pending

    def _get_exposed_block(self, queryset):
        latest_contact_tag = UserContacts.objects.filter(
            user=OuterRef('pk'),
            is_infected=True
        ).order_by('-date_contacted').values('date_contacted')

        latest_location_tag = UserLocations.objects.filter(
            user=OuterRef('pk'),
            is_infected=True
        ).order_by('-location_date').values('location_date')

        latest_flight_tag = FlightDetails.objects.filter(
            user=OuterRef('pk'),
            is_infected=True
        ).order_by('-date_journey').values('date_journey')

        latest_test_date = Subquery(UserTesting.objects.filter(
            user_id=OuterRef("id"),
        ).order_by("-tested_date").values('tested_date')[:1])

        latest_test_result = Subquery(UserTesting.objects.filter(
            user_id=OuterRef("id"),
        ).order_by("-tested_date").values('test_result')[:1])

        exposed_users = queryset.annotate(
            date_contacted=Subquery(latest_contact_tag)
        ).annotate(
            location_date=Subquery(latest_location_tag)
        ).annotate(
            date_journey=Subquery(latest_flight_tag)
        ).annotate(
            last_infected=Greatest(
                'date_contacted',
                'location_date',
                'date_journey'
            )
        ).annotate(
            latest_test_date=latest_test_date
        ).annotate(
            latest_test_result=latest_test_result
        ).filter(last_infected__isnull=False).distinct()

        negative = exposed_users.filter(
            latest_test_result='Negative',
            last_infected__lte=F('latest_test_date')
        ).count()
        positive = exposed_users.filter(
            latest_test_result='Positive',
            last_infected__lte=F('latest_test_date')
        ).count()
        no_response = exposed_users.filter(
            Q(
                Q(latest_test_date__isnull=True) |
                Q(latest_test_date__lt=F('last_infected'))
            ) &
            Q(last_infected__lte=timezone.now() - timezone.timedelta(days=15))
        ).count()
        pending = exposed_users.filter(
            Q(
                Q(latest_test_date__isnull=True) |
                Q(latest_test_date__lt=F('last_infected'))
            ) &
            Q(last_infected__gt=timezone.now() - timezone.timedelta(days=15))
        ).count()

        return negative, positive, no_response, pending

    def get_response_data(self, request, queryset):
        (testing_negative,
         testing_positive,
         testing_no_response,
         testing_pending) = self._get_testing_block(queryset)
        (exposed_negative,
         exposed_positive,
         exposed_no_response,
         exposed_pending) = self._get_exposed_block(queryset)

        return {
            'testing_negative': testing_negative,
            'testing_positive': testing_positive,
            'testing_no_response': testing_no_response,
            'testing_pending': testing_pending,
            'exposed_negative': exposed_negative,
            'exposed_positive': exposed_positive,
            'exposed_no_response': exposed_no_response,
            'exposed_pending': exposed_pending
        }

    def get(self, request, organisation_id, format=None):
        if organisation_id is None:
            raise ValidationError('Missed organisation_id parameter')
        try:
            organisation = OrganizationProfile.objects.get(id=organisation_id)
            organisation_users = User.objects.filter(userorganization__organization=organisation)
            data = self.get_response_data(request, organisation_users)
            data['organization_name'] = organisation.organization_name
            return Response(data, status=status.HTTP_200_OK)
        except OrganizationProfile.DoesNotExist:
            raise NotFound(f'Organisation with id={organisation_id} not found')


class DashboardChartGraphView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organisation_id, format=None):
        if organisation_id is None:
            raise ValidationError('Missed organisation_id parameter')
        try:
            organisation = OrganizationProfile.objects.get(id=organisation_id)
            organisation_users = User.objects.filter(userorganization__organization=organisation)
            dashboard_filter = DashboardChartGraphFilter(request.query_params)
            data = dashboard_filter.filter_queryset(request, organisation_users, self)
            return Response(data, status=status.HTTP_200_OK)
        except OrganizationProfile.DoesNotExist:
            raise NotFound(f'Organisation with id={organisation_id} not found')


class DashboardResultsView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organisation_id, format=None):
        if organisation_id is None:
            raise ValidationError('Missed organisation_id parameter')
        try:
            organisation = OrganizationProfile.objects.get(id=organisation_id)
            organisation_users = User.objects.filter(userorganization__organization=organisation)
            dashboard_filter = DashboardResultsFilter(request)
            data = dashboard_filter.filter_queryset(request, organisation_users, self)
            return Response(data, status=status.HTTP_200_OK)
        except OrganizationProfile.DoesNotExist:
            raise NotFound(f'Organisation with id={organisation_id} not found')
