from django.db.models import Q, Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear
from django.utils import timezone
from rest_framework import filters
from rest_framework.exceptions import ValidationError

from apps.covid19.contacts.models import UserContacts
from apps.covid19.covid_accounts.models import ScreeningUser
from apps.covid19.covid_accounts.models import UserTesting
from apps.covid19.flight.models import FlightDetails
from apps.covid19.location.models import UserLocations

PERIOD_DAYS = {
    'day': 1,
    'week': 7,
    'month': 30,
    'year': 365,
}

DELTA_TRUNC = {
    'day': TruncDay,
    'week': TruncWeek,
    'month': TruncMonth,
    'year': TruncYear
}

CHART_DAYS = {
    'day': 30,
    'week': 210,  # 30 weeks in days
    'month': 365,  # 1 year in days
    'year': 4380  # 12 years in days
}


class DashboardResultsFilter(filters.BaseFilterBackend):
    def __init__(self, request):
        """
        Initialisation of required parameters
        """
        super().__init__()
        parameter_names = ['people_delta', 'tracing_delta', 'testing_delta']
        if not all(p_name in request.query_params for p_name in parameter_names):
            raise ValidationError('Missed on of the required parameters: people_delta, '
                                  'tracing_delta, testing_delta')
        self.people_delta = request.query_params.get('people_delta')
        self.tracing_delta = request.query_params.get('tracing_delta')
        self.testing_delta = request.query_params.get('testing_delta')

        period_parameters = [self.people_delta, self.tracing_delta, self.testing_delta]
        # parameters validation
        if not all(p in PERIOD_DAYS.keys() for p in period_parameters):
            raise ValidationError('Period parameters must have one of values: `day`, `week`, '
                                  '`month`, `year`')

    def _get_people_block(self, queryset):
        date_start = timezone.now() - timezone.timedelta(days=PERIOD_DAYS[self.people_delta])
        devices = queryset.filter(
            (
                Q(user_contact__user_contact_tagging__isnull=False) &
                Q(user_contact__user_contact_tagging__user_contact__date_contacted__gte=date_start)
            ) | (
                Q(user_locations__user_location_tagging__isnull=False) &
                Q(user_locations__user_location_tagging__user_location__location_date__gte=
                  date_start)
            ) | (
                Q(user_flight__isnull=False) &
                Q(user_flight__date_journey__gte=date_start)
            )
        ).distinct().count()

        check_ins = ScreeningUser.objects.filter(created_at__gte=date_start).count()

        subscribers = queryset.filter(is_subscribed=True).count()
        return devices, check_ins, subscribers

    def _get_tracing_block(self, queryset):
        date_start = timezone.now() - timezone.timedelta(days=PERIOD_DAYS[self.tracing_delta])
        users_with_contact_tag_expr = (
                Q(user_contact__isnull=False) &
                Q(user_contact__date_contacted__gte=date_start) &
                Q(user_contact__is_infected=True)
        )

        users_with_location_tag_expr = (
                Q(user_locations__isnull=False) &
                Q(user_locations__location_date__gte=date_start) &
                Q(user_locations__is_infected=True)
        )

        users_with_flight_tag_expr = (
                Q(user_flight__isnull=False) &
                Q(user_flight__date_journey__gte=date_start) &
                Q(user_flight__is_infected=True)
        )

        exposed = queryset.filter(Q(users_with_contact_tag_expr | users_with_location_tag_expr |
                                    users_with_flight_tag_expr)).distinct().count()

        notified = queryset.filter(
            notificationhistoryuser__notification_type='high-risk-area',
            notificationhistoryuser__date_created__gte=date_start
        ).distinct().count()

        responded = queryset.filter(
            notificationhistoryuser__notification_type='high-risk-area',
            notificationhistoryuser__date_created__gte=date_start,
            notificationhistoryuser__is_read=True
        ).distinct().count()

        return exposed, notified, responded

    def _get_testing_block(self, queryset):
        date_start = timezone.now() - timezone.timedelta(days=PERIOD_DAYS[self.testing_delta])
        if timezone.now() - timezone.timedelta(days=15) > date_start:
            pending_date_start = timezone.now() - timezone.timedelta(days=15)
        else:
            pending_date_start = date_start
        pending = queryset.filter(
            notificationhistoryuser__notification_type='high-risk-area',
            notificationhistoryuser__date_created__gte=date_start,
            notificationhistoryuser__is_read=True
        ).exclude(user_testing__tested_date__gte=pending_date_start).distinct().count()

        positive = queryset.filter(
            user_testing__tested_date__gte=date_start,
            user_testing__test_result='Positive'
        ).distinct().count()

        negative = queryset.filter(
            user_testing__tested_date__gte=date_start,
            user_testing__test_result='Negative'
        ).distinct().count()

        return pending, positive, negative

    def filter_queryset(self, request, queryset, view):
        devices, check_ins, subscribers = self._get_people_block(queryset)
        exposed, notified, responded = self._get_tracing_block(queryset)
        pending, positive, negative = self._get_testing_block(queryset)
        return {
            'devices': devices,
            'check_ins': check_ins,
            'subscribers': subscribers,
            'exposed': exposed,
            'notified': notified,
            'responded': responded,
            'pending': pending,
            'positive': positive,
            'negative': negative
        }


class DashboardChartGraphFilter(filters.BaseFilterBackend):
    def __init__(self, query_params):
        """
        Initialisation of required parameters
        """
        super().__init__()
        parameter_names = ['charts', 'delta', 'show_weekday']
        if not all(p_name in query_params for p_name in parameter_names):
            raise ValidationError('Missed on of the required parameters: charts, '
                                  'delta, show_weekday')
        self.charts = query_params.get('charts').split(',')
        self.delta = query_params.get('delta')
        self.show_weekday = query_params.get('show_weekday')

        # parameters validation
        for chart in self.charts:
            if chart not in ['cases', 'testing']:
                raise ValidationError('Charts list must consists of cases and testing charts')
        if self.delta not in PERIOD_DAYS.keys():
            raise ValidationError('Delta must have one of values: `day`, `week`, '
                                  '`month`, `year`')

    def _get_cases_expr(self, date_start, date_end):
        if self.show_weekday:
            start_weekday = 2
            end_weekday = 6
        else:
            start_weekday = 1
            end_weekday = 7

        users_with_contact_tag_expr = (
                Q(user_contact__isnull=False) &
                Q(user_contact__date_contacted__gte=date_start) &
                Q(user_contact__date_contacted__lte=date_end) &
                Q(user_contact__date_contacted__week_day__gte=start_weekday) &
                Q(user_contact__date_contacted__week_day__lte=end_weekday)
        )

        users_with_location_tag_expr = (
                Q(user_locations__isnull=False) &
                Q(user_locations__location_date__gte=date_start) &
                Q(user_locations__location_date__lte=date_end) &
                Q(user_locations__location_date__week_day__gte=start_weekday) &
                Q(user_locations__location_date__week_day__lte=end_weekday)
        )

        users_with_flight_tag_expr = (
                Q(user_flight__isnull=False) &
                Q(user_flight__date_journey__gte=date_start) &
                Q(user_flight__date_journey__lte=date_end) &
                Q(user_flight__date_journey__week_day__gte=start_weekday) &
                Q(user_flight__date_journey__week_day__lte=end_weekday)
        )

        return (users_with_contact_tag_expr | users_with_location_tag_expr |
                users_with_flight_tag_expr)

    def _get_testing(self, queryset):
        tests = UserTesting.objects.filter(user__in=queryset)
        if self.show_weekday:
            tests = tests.filter(tested_date__week_day__gte=2, tested_date__week_day__lte=6)
        tests = tests.filter(
            tested_date__gte=timezone.now() - timezone.timedelta(days=CHART_DAYS[self.delta]))
        return tests.annotate(date=DELTA_TRUNC[self.delta]('tested_date')).values('date').annotate(
            count=Count('id')).order_by()

    def _get_cases(self, queryset):

        def _get_cases_objects(days_delta):
            if self.show_weekday:
                start_weekday = 2
                end_weekday = 6
            else:
                start_weekday = 1
                end_weekday = 7
            date_start = timezone.now() - timezone.timedelta(days=days_delta)
            contacts_objects = UserContacts.objects.filter(
                user__in=queryset, date_contacted__gte=date_start,
                date_contacted__week_day__gte=start_weekday,
                date_contacted__week_day__lte=end_weekday
            )
            locations_objects = UserLocations.objects.filter(
                user__in=queryset, location_date__gte=date_start,
                location_date__week_day__gte=start_weekday,
                location_date__week_day__lte=end_weekday
            )
            flights_objects = FlightDetails.objects.filter(
                user__in=queryset, date_journey__gte=date_start,
                date_journey__week_day__gte=start_weekday,
                date_journey__week_day__lte=end_weekday
            )
            return contacts_objects, locations_objects, flights_objects

        dates_dict = {}

        contacts, locations, flights = _get_cases_objects(CHART_DAYS[self.delta])
        contacts = contacts.annotate(date=DELTA_TRUNC[self.delta]('date_contacted')).values(
            'date').annotate(count=Count('id')).order_by()
        locations = locations.annotate(date=DELTA_TRUNC[self.delta]('location_date')).values(
            'date').annotate(count=Count('id')).order_by()
        flights = flights.annotate(date=DELTA_TRUNC[self.delta]('date_journey')).values(
            'date').annotate(count=Count('id')).order_by()
        dates = contacts.union(locations, flights, all=True)

        for date in dates:
            dates_dict[date['date']] = dates_dict.get(date['date'], 0) + date['count']
        dates_list = [{'date': k, 'count': v} for k, v in dates_dict.items()]
        return sorted(dates_list, key=lambda k: k['date'])

    def filter_queryset(self, request, queryset, view):
        # Total cases(all the users with at least one contact tag or location tag)
        last_start = timezone.now() - timezone.timedelta(days=PERIOD_DAYS[self.delta])
        total_cases_count = queryset.filter(
            self._get_cases_expr(last_start, timezone.now())).distinct().count()

        previous_start = last_start - timezone.timedelta(days=PERIOD_DAYS[self.delta])
        previous_cases_count = queryset.filter(
            self._get_cases_expr(previous_start, last_start)).distinct().count()
        if previous_cases_count:
            cases_change = round((total_cases_count - previous_cases_count) /
                                 previous_cases_count * 100)
        elif not previous_cases_count and total_cases_count > previous_cases_count:
            cases_change = 100
        else:
            cases_change = 0

        data = {
            'total_cases': total_cases_count,
            'cases_change': cases_change,
        }

        if 'testing' in self.charts:
            data['testing'] = self._get_testing(queryset)
        if 'cases' in self.charts:
            data['cases'] = self._get_cases(queryset)

        return data
