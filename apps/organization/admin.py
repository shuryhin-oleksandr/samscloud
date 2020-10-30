from django.contrib import admin
from .models import OrganizationProfile, OrganizationContact, OrganizationType, \
    UserOrganization, OrganizationFloors, Zone, ZoneDocument, ZoneCCTV, OrganizationGeoFence, ZoneFloor, \
    EmergencyContact, OrganizationAddress, OrganizationMessage


class OrganizationProfileModelAdmin(admin.ModelAdmin):
    search_fields = ('organization_name',)
    list_display = ['organization_name', 'contact_name', 'organization_type', 'is_email_verified', 'number_of_floors']


class OrganizationContactModelAdmin(admin.ModelAdmin):
    search_fields = ('organization__organization_name',)
    list_display = ['organization', 'user', 'name', 'contact_role', 'uuid']


class OrganizationTypeModelAdmin(admin.ModelAdmin):
    list_display = ['type_name', 'is_active']


class UserOrganizationModelAdmin(admin.ModelAdmin):
    search_fields = ('organization__organization_name', 'user__first_name')
    list_display = ['user', 'organization']


class EmergencyContactModelAdmin(admin.ModelAdmin):
    search_fields = ('name', 'email', 'status', 'contact_type')
    list_display = ['user', 'name', 'phone_number', 'email', 'status', 'contact_type', 'uuid']


admin.site.register(OrganizationProfile, OrganizationProfileModelAdmin)
admin.site.register(OrganizationContact, OrganizationContactModelAdmin)
admin.site.register(OrganizationType, OrganizationTypeModelAdmin)
admin.site.register(UserOrganization, UserOrganizationModelAdmin)
admin.site.register(EmergencyContact, EmergencyContactModelAdmin)
admin.site.register(OrganizationAddress)
admin.site.register(OrganizationFloors)
admin.site.register(OrganizationGeoFence)
admin.site.register(ZoneCCTV)
admin.site.register(Zone)
admin.site.register(ZoneDocument)
admin.site.register(ZoneFloor)
admin.site.register(OrganizationMessage)
