from django.db.models import Q
from django.utils import timezone
from rest_framework import filters
from rest_framework.exceptions import ValidationError

PERIOD_DAYS = {
    'day': 1,
    'week': 7,
    'month': 30,
    'year': 365,
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

        # TODO add check_ins count logic
        check_ins = 0

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
