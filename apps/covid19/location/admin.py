from django.contrib import admin

# Register your models here.
from apps.covid19.location.models import UserLocations, GlobalLocations, AssistanceLocations


class UserLocationsReview(UserLocations):
    class Meta:
        proxy = True
        app_label = 'covid_accounts'
        verbose_name = 'User Locations'
        verbose_name_plural = 'User Locations'


class GlobalLocationsReview(GlobalLocations):
    class Meta:
        proxy = True
        app_label = 'covid_accounts'
        verbose_name = 'Global Locations'
        verbose_name_plural = 'Global Locations'


class AssistanceLocationsReview(AssistanceLocations):
    class Meta:
        proxy = True
        app_label = 'covid_accounts'
        verbose_name = 'Assistance Locations'
        verbose_name_plural = 'Assistance Locations'


# in admin.py
admin.site.register(UserLocationsReview)
admin.site.register(GlobalLocationsReview)
admin.site.register(AssistanceLocationsReview)
