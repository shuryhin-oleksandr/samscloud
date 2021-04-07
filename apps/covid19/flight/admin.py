from django.contrib import admin

# Register your models here.
from apps.covid19.flight.models import Flight, FlightDetails, UserAnswers, Questions


class FlightReview(Flight):
    class Meta:
        proxy = True
        app_label = 'covid_accounts'
        verbose_name = Flight._meta.verbose_name
        verbose_name_plural = Flight._meta.verbose_name_plural


class FlightDetailsReview(FlightDetails):
    class Meta:
        proxy = True
        app_label = 'covid_accounts'
        verbose_name = 'Flight Details'
        verbose_name_plural = 'Flight Details'


class UserAnswersReview(UserAnswers):
    class Meta:
        proxy = True
        app_label = 'covid_accounts'
        verbose_name = 'User Answers'
        verbose_name_plural = 'User Answers'


class QuestionsReview(Questions):
    class Meta:
        proxy = True
        app_label = 'covid_accounts'
        verbose_name = 'Questions'
        verbose_name_plural = 'Questions'


# in admin.py
admin.site.register(FlightReview)
admin.site.register(FlightDetailsReview)
admin.site.register(UserAnswersReview)
admin.site.register(QuestionsReview)
