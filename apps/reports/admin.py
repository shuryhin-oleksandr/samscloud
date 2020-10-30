from django.contrib import admin
from .models import ReportType, Report, ReportFile, NotificationSettings, CurrentUserLocation, NotificationHistory, \
    UserGeofences, UserGeofenceStatus

admin.site.register(ReportType)
admin.site.register(Report)
admin.site.register(ReportFile)
admin.site.register(NotificationSettings)
admin.site.register(CurrentUserLocation)
admin.site.register(NotificationHistory)
admin.site.register(UserGeofences)
admin.site.register(UserGeofenceStatus)