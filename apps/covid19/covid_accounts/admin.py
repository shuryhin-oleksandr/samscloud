from django.contrib import admin

from apps.covid19.covid_accounts.models import (UserReport, Status, Lastupdated, UserTesting,
                                                Screening, ScreeningQuestion, ScreeningAnswer,
                                                ScreeningUser, ScreeningQuestionOption)

admin.site.register(UserReport),
admin.site.register(Status),
admin.site.register(Lastupdated)
admin.site.register(UserTesting)
admin.site.register(Screening)
admin.site.register(ScreeningQuestion)
admin.site.register(ScreeningAnswer)
admin.site.register(ScreeningQuestionOption)
admin.site.register(ScreeningUser)
