from django.contrib import admin

from .models import Incident, IncidentJoinedResponder, IncidentUrlTracker, ReporterLocationTracker


# Register your models here.

class IncidentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'organization', 'emergency_message', 'address',)


class IncidentJoinedResponderAdmin(admin.ModelAdmin):
    list_display = ('__str__',)


class ReporterLocationTrackerAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'latitude', 'longitude', 'address')


admin.site.register(Incident, IncidentAdmin)
admin.site.register(IncidentJoinedResponder, IncidentJoinedResponderAdmin)
admin.site.register(IncidentUrlTracker)
admin.site.register(ReporterLocationTracker, ReporterLocationTrackerAdmin)
