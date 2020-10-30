import requests
import json
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from twilio.rest import Client
from rest_framework_simplejwt.tokens import RefreshToken
from celery.decorators import task
from fcm_django.models import FCMDevice

from apps.incident.models import Incident
from apps.organization.models import OrganizationContact


def send_user_notification(incident_id, org_obj):
    data = {}
    try:

        obj = Incident.objects.get(id=incident_id)
        data["uuid"] = str(org_obj.uuid)
        data["latitude"] = obj.latitude
        data["longitude"] = obj.longitude
        data["incident_id"] = str(incident_id)
        if obj.streaming_id:
            data["streaming_id"] = obj.streaming_id
        else:
            data["streaming_id"] = ""
    except:
        obj = False
    return str(data)

def save_incident_duration(incident_id, vod_id):
    vod_url = 'https://antmedia.samscloud.io:5443/WebRTCAppEE/rest/v2/vods/' + vod_id
    try:
        vod_response = requests.get(vod_url)
        if vod_response.status_code == 200:
            response = json.loads(vod_response.content)
            stream_duration = response['duration']
            save_incident_duration_to_model(incident_id, stream_duration)
    except Exception as e:
        print("Unable to save the incident duration due to ", e)

@task(name="save video duration")
def save_incident_duration_to_model(incident_id, stream_duration):
    incident_obj = Incident.objects.get(id=incident_id)
    incident_obj.stream_duration = stream_duration
    incident_obj.save()