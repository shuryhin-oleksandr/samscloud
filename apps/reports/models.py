import datetime
import random
import string

from django.contrib.postgres.fields import ArrayField
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from django.contrib.auth import get_user_model
from fcm_django.models import FCMDevice

from apps.accounts.models import TimeStampedModel
from apps.organization.models import OrganizationProfile, Zone, ZoneFloor, EmergencyContact
from django.contrib.postgres.fields import JSONField
from apps.accounts.api.utils import send_push_notification
User = get_user_model()


class ReportType(models.Model):
    name = models.CharField(max_length=30)

    def __str__(self):
        return self.name


class Report(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    maintenance_id = models.CharField(max_length=20, blank=True, null=True, unique=True)
    details = models.TextField()
    address = models.CharField(max_length=100, blank=True, null=True)
    latitude = models.CharField(max_length=10, blank=True, null=True)
    longitude = models.CharField(max_length=10, blank=True, null=True)
    reporting_organizations = models.ManyToManyField(OrganizationProfile, related_name="organization_reports", blank=True)
    organization = models.ForeignKey(OrganizationProfile, null=True, blank=True, on_delete=models.CASCADE)
    report_zone = models.ForeignKey(Zone, on_delete=models.CASCADE,  null=True, blank=True)
    report_zone_floor = models.ForeignKey(ZoneFloor, on_delete=models.CASCADE,  null=True, blank=True)
    send_anonymously = models.BooleanField(default=False, blank=True, null=True)

    def __str__(self):
        return self.report_type.name


@receiver(post_save, sender=Report)
def create_report(sender, instance, created, **kwargs):
    if created:
        timestamp = datetime.datetime.now().strftime('%d%m')
        report_id = instance.id
        random_string = random.choice(string.ascii_uppercase)
        maintenance_id = str(report_id) + str(timestamp) + random_string
        instance.maintenance_id = maintenance_id
        instance.save()


def report_directory_path(instance, filename):
    return 'reports/{0}/{1}'.format(instance.file_report.maintenance_id, filename)


class ReportFile(TimeStampedModel):
    file = models.FileField(upload_to=report_directory_path)
    file_report = models.ForeignKey(Report, on_delete=models.CASCADE)


class NotificationSettings(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notificationuser")
    new_message = models.BooleanField(default=True, blank=True, null=True)
    contact_request = models.BooleanField(default=True, blank=True, null=True)
    contact_disable_location = models.BooleanField(default=True, blank=True, null=True)
    crisis_emergency_alert = models.BooleanField(default=True, blank=True, null=True)
    contact_has_incident = models.BooleanField(default=True, blank=True, null=True)
    send_incident_text = models.BooleanField(default=True, blank=True, null=True)
    send_incident_email = models.BooleanField(default=False, blank=True, null=True)
    app_tips = models.BooleanField(default=True, blank=True, null=True)
    new_updates = models.BooleanField(default=True, blank=True, null=True)
    exposed_locations = models.BooleanField(default=True, blank=True, null=True)
    infected_contact = models.BooleanField(default=True, blank=True, null=True)
    traced_exposure = models.BooleanField(default=True, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    """
    settings preferences
    """
    bluetooth = models.BooleanField(default=True, blank=True, null=True)
    nfc = models.BooleanField(default=True, blank=True, null=True)
    siri_incident_start = models.BooleanField(default=True, blank=True, null=True)
    auto_route_incident_organization = models.BooleanField(default=False, blank=True, null=True)
    auto_route_contacts = models.BooleanField(default=False, blank=False, null=True)
    shake_activate_incident = models.BooleanField(default=True, blank=True, null=True)
    def __str__(self):
        return self.user.first_name



class CurrentUserLocation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="currentlocationuser")
    share_location = models.BooleanField(default=False, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.CharField(max_length=100, null=True, blank=True)
    longitude = models.CharField(max_length=100, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.user.first_name

class NotificationHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notificationhistoryuser")
    requested_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="requesteduser", null=True, blank=True)
    requested_token = models.CharField(max_length=200, null=True, blank=True)
    array_data = ArrayField(models.CharField(max_length=255), blank=True,  null=True)
    attribute = JSONField(blank=True,  null=True)
    notification_type = models.CharField(max_length=100, null=True, blank=True)
    message = models.CharField(max_length=255, null=True, blank=True)
    title = models.CharField(max_length=200, null=True, blank=True)
    is_read = models.BooleanField(default=False, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.email

class UserGeofences(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="geofenceuser")
    assign_contacts = models.ManyToManyField(EmergencyContact, blank=True, related_name="geofencecontacts")
    assign_mangers = models.ManyToManyField(EmergencyContact, blank=True, related_name="geofencemanager")
    name = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.CharField(max_length=100, null=True, blank=True)
    longitude = models.CharField(max_length=100, blank=True, null=True)
    radius = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    from_time = models.TimeField(blank=True, null=True)
    to_time = models.TimeField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.user.first_name

# # method for updating
# @receiver(post_save, sender=UserGeofences, dispatch_uid="send_request_checkin")
# def update_geofence(sender, instance, **kwargs):
#     if instance.assign_contacts:
#         for emergency in instance.assign_contacts.all():
#             contact_obj = EmergencyContact.objects.filter(id=emergency)
#             if contact_obj[0].email is not None:
#                 user_obj = User.objects.filter(email=contact_obj[0].email)
#             if contact_obj[0].phone_number is not None:
#                 user_obj = User.objects.filter(phone_number=contact_obj[0].phone_number)
#             if user_obj is not None:
#                 qs = FCMDevice.objects.filter(user=user_obj[0])
#                 if qs.exists():
#                     fcm_obj = qs.first()
#                     data = {
#                         "type": "geofence-request-check-in",
#                         "emergency-contact": contact_obj[0].id,
#                         "geo-fence": instance.id,
#                         "geofence-type": "contact"
#                     }
#                     message = "%s is requesting a geo fence check-in" % (
#                         instance.user.first_name)
#                     title = "Request to Geo Fence checkIn"
#                     send_push_notification.delay(fcm_obj.id, title, message, data)
#                     histroy = NotificationHistory(user=user_obj.first(), requested_user=instance.user, attribute=data,
#                                                   notification_type="request-geofence-check-in", message=message,
#                                                   title=title)
#                     histroy.save()
#     if instance.assign_mangers:
#         instance_emergency = instance.assign_mangers
#         for emergency in instance_emergency:
#             contact_obj = EmergencyContact.objects.filter(id=emergency)
#             if contact_obj[0].email is not None:
#                 user_obj = User.objects.filter(email=contact_obj[0].email)
#             if contact_obj[0].phone_number is not None:
#                 user_obj = User.objects.filter(phone_number=contact_obj[0].phone_number)
#             if user_obj is not None:
#                 qs = FCMDevice.objects.filter(user=user_obj[0])
#                 if qs.exists():
#                     fcm_obj = qs.first()
#                     data = {
#                         "type": "geofence-request-check-in",
#                         "emergency-contact": contact_obj[0].id,
#                         "geo-fence": instance.id,
#                         "geofence-type": "manager"
#                     }
#                     message = "%s is requesting a geo fence check-in" % (
#                         instance.user.first_name)
#                     title = "Request to Geo Fence checkIn"
#                     send_push_notification.delay(fcm_obj.id, title, message, data)
#                     histroy = NotificationHistory(user=user_obj.first(), requested_user=instance.user, attribute=data,
#                                                   notification_type="request-geofence-check-in", message=message,
#                                                   title=title)
#                     histroy.save()w   

CONTACTS_STATUS = (
    ('Pending', 'Pending'),
    ('Accepted', 'Accepted'),
    ('Rejected', 'Rejected'),
)

CONTACT_TYPE = (
    ('Manager', 'Manager'),
    ('Contact', 'Contact'),
)
class UserGeofenceStatus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="assignedgeofenceuser", blank=True, null=True)
    geofence = models.ForeignKey(UserGeofences, on_delete=models.CASCADE, related_name="assignedgeofence", blank=True, null=True)
    emergency = models.ForeignKey(EmergencyContact, on_delete=models.CASCADE, related_name="assignedemergency", blank=True, null=True)
    is_hidden = models.BooleanField(default=False, blank=True, null=True)
    request_status = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=CONTACTS_STATUS, default="Pending")
    contact_type = models.CharField(max_length=20, blank=True, null=True, choices=CONTACT_TYPE)
    date_created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.contact_type

