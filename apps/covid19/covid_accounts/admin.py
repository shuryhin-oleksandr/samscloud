from django.contrib import admin

# Register your models here.
from apps.covid19.covid_accounts.models import UserReport, Status, Lastupdated, UserTesting

admin.site.register(UserReport),
admin.site.register(Status),
admin.site.register(Lastupdated)
admin.site.register(UserTesting)