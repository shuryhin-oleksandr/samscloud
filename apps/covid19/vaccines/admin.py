from django.contrib import admin

# Register your models here.
from apps.covid19.vaccines.models import UserVaccine, Dose, Manufacturer


class UserVaccineReview(UserVaccine):
    class Meta:
        proxy = True
        app_label = 'covid_accounts'
        verbose_name = 'User Vaccines'
        verbose_name_plural = 'User Vaccines'


class DoseReview(Dose):
    class Meta:
        proxy = True
        app_label = 'covid_accounts'
        verbose_name = Dose._meta.verbose_name
        verbose_name_plural = Dose._meta.verbose_name_plural


class ManufacturerReview(Manufacturer):
    class Meta:
        proxy = True
        app_label = 'covid_accounts'
        verbose_name = Manufacturer._meta.verbose_name
        verbose_name_plural = Manufacturer._meta.verbose_name_plural


# in admin.py
admin.site.register(UserVaccineReview)
admin.site.register(DoseReview)
admin.site.register(ManufacturerReview)
