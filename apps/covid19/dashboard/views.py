from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import User
from apps.covid19.dashboard.filters import DashboardResultsFilter, DashboardChartGraphFilter
from apps.organization.models import OrganizationProfile


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
