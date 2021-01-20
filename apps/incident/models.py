from django.db import models
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.db.models import signals
import json
import requests
from apps.accounts.models import TimeStampedModel
from apps.organization.models import OrganizationProfile, EmergencyContact, OrganizationContact

# Create your models here.

User = get_user_model()


class Incident(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(OrganizationProfile, on_delete=models.SET_NULL, null=True, blank=True)
    latitude = models.CharField(blank=True, null=True, max_length=20)
    longitude = models.CharField(blank=True, null=True, max_length=20)
    altitude = models.CharField(blank=True, null=True, max_length=20)
    emergency_message = models.CharField(blank=True, null=True, max_length=50)
    address = models.TextField(blank=True, null=True)
    ending_message = models.CharField(blank=True, null=True, max_length=50)
    streaming_id = models.CharField(blank=True, null=True, max_length=30)
    room_id = models.CharField(blank=True, null=True, max_length=30)
    vod_id = models.CharField(blank=True, null=True, max_length=50)
    vod_name = models.CharField(blank=True, null=True, max_length=50)
    stream_duration = models.CharField(blank=True, null=True, max_length=50)
    is_started = models.BooleanField(default=False)
    is_ended = models.BooleanField(default=False)
    is_stopped = models.BooleanField(default=False)
    stream_thumbnail = models.ImageField(upload_to='incident-images', blank=True, null=True)

    def __str__(self):
        return self.user.first_name


@receiver(signals.post_save, sender=Incident)
def create_pro_code(sender, instance, **kwargs):
    if not instance.room_id:
        room_id = str(instance.id) + str(instance.created_at.year) + str(instance.created_at.month) + str(
            instance.created_at.day)
        data = {"roomId": room_id}
        url = 'https://antmedia.samscloud.io:5443/LiveApp/rest/v2/broadcasts/conference-rooms'
        headers = {'content-type': 'application/json'}
        response = requests.post(url=url, data=json.dumps(data), verify=False, headers=headers)
        if response.status_code == 200:
            response_data = json.loads(response.text)
            room_id = response_data['roomId']
            instance.room_id = room_id
            instance.save()


class IncidentJoinedResponder(TimeStampedModel):
    user_incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='ongoing_incident')
    emergency_contact = models.ForeignKey(EmergencyContact, blank=True,
                                          related_name='joined_emergency_contact', on_delete=models.CASCADE, null=True)
    organization_contact = models.ForeignKey(OrganizationContact, blank=True, null=True,
                                             related_name='joined_organization_contact', on_delete=models.CASCADE)

    stream_id = models.CharField(max_length=100, blank=True, null=True)
    vod_id = models.CharField(blank=True, null=True, max_length=50)
    vod_name = models.CharField(blank=True, null=True, max_length=50)

    def __str__(self):
        return str(self.user_incident)


class IncidentUrlTracker(TimeStampedModel):
    key = models.CharField(max_length=255, unique=True)
    url = models.CharField(max_length=200)

    def __str__(self):
        return str(self.key)


class ReporterLocationTracker(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reporter_incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='user_incident')
    latitude = models.CharField(max_length=20, blank=True, null=True)
    altitude = models.CharField(max_length=20, blank=True, null=True)
    longitude = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.first_name
