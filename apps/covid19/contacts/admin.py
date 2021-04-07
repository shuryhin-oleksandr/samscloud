from django.contrib import admin

# Register your models here.
from apps.covid19.contacts.models import Symptoms, Disease, UserContacts


class DiseaseReview(Disease):
    class Meta:
        proxy = True
        app_label = 'covid_accounts'
        verbose_name = Disease._meta.verbose_name
        verbose_name_plural = Disease._meta.verbose_name_plural


class SymptomsReview(Symptoms):
    class Meta:
        proxy = True
        app_label = 'covid_accounts'
        verbose_name = 'Symptoms'
        verbose_name_plural = 'Symptoms'


class UserContactsReview(UserContacts):
    class Meta:
        proxy = True
        app_label = 'covid_accounts'
        verbose_name = 'User Contacts'
        verbose_name_plural = 'User Contacts'


# in admin.py
admin.site.register(DiseaseReview)
admin.site.register(SymptomsReview)
admin.site.register(UserContactsReview)
