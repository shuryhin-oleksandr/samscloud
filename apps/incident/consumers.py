import asyncio
import json
from django.db.models import Q
import ast
from django.contrib.auth import get_user_model
from channels.consumer import SyncConsumer, AsyncConsumer
from channels.db import database_sync_to_async

from apps.incident.models import ReporterLocationTracker, Incident, IncidentJoinedResponder
from apps.organization.models import OrganizationContact

User = get_user_model()


class ReportLocationConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        self.incident_id = self.scope['url_route']['kwargs']['pk']
        broadcast_room = f"incident_{self.incident_id}"
        self.broadcast_room = broadcast_room
        await self.channel_layer.group_add(
            broadcast_room,
            self.channel_name
        )
        await self.send({
            "type": "websocket.accept"
        })

    async def websocket_receive(self, event):  # websocket.receive
        data = event.get("text", None)
        if data:
            try:
                user_data = ast.literal_eval(data)
                if user_data['action'] == 'conference_room':
                    response = await self.save_responder_stream(user_data)
                    response_data = {**user_data, **response}
                    await self.channel_layer.group_send(
                        self.broadcast_room,
                        {
                            "type": "broadcast_message",
                            "text": str(response_data).replace("'", '"')
                        }
                    )
                else:
                    await self.create_user_locations(user_data)
                    await self.channel_layer.group_send(
                        self.broadcast_room,
                        {
                            "type": "broadcast_message",
                            "text": str(user_data).replace("'", '"')
                        }
                    )
            except Exception as e:
                error_data = {"status": "error", "message": e}
                await self.channel_layer.group_send(
                    self.broadcast_room,
                    {
                        "type": "broadcast_message",
                        "text": str(error_data).replace("'", '"')
                    }
                )

    async def broadcast_message(self, event):
        await self.send({
            "type": "websocket.send",
            "text": event['text']
        })

    async def websocket_disconnect(self, event):
        print('disconnect', event)

    @database_sync_to_async
    def create_user_locations(self, data):
        latitude = data['latitude']
        longitude = data['longitude']
        altitude = data['altitude']
        user = data['user_id']
        incident = data['incident_id']
        address = data['address']
        try:
            obj = ReporterLocationTracker.objects.create(user_id=user, reporter_incident_id=incident, latitude=latitude,
                                                         longitude=longitude, altitude=altitude, address=address)
        except:
            obj = False
        return obj

    @database_sync_to_async
    def save_responder_stream(self, data):
        incident_id = data['incident_id']
        uuid = data['uuid']
        stream_id = data['stream_id']
        responder_obj = None
        responder_name = "Not Available"
        responder_image = "Not Available"
        responder_email = None
        responder_phone_number = None
        try:
            responder_obj = IncidentJoinedResponder.objects.get(user_incident_id=incident_id,
                                                                emergency_contact__uuid=uuid)
            responder_name = responder_obj.emergency_contact.name
            responder_email = responder_obj.emergency_contact.email
            responder_phone_number = responder_obj.emergency_contact.phone_number
        except Exception as e:
            pass
        try:
            responder_obj = IncidentJoinedResponder.objects.get(user_incident_id=incident_id,
                                                                organization_contact__uuid=uuid)
            responder_name = responder_obj.organization_contact.name
            responder_email = responder_obj.organization_contact.email
            responder_phone_number = responder_obj.organization_contact.phone_number
        except Exception as e:
            pass
        if responder_obj:
            responder_obj.stream_id = stream_id
            responder_obj.save()
            user_qs = User.objects.filter(Q(email=responder_email)|Q(phone_number=responder_phone_number))
            if user_qs.exists():
                user_obj = user_qs.first()
                try:
                    responder_image = user_obj.profile_logo.url
                except:
                    pass
        data = {
            "responder_name": responder_name,
            "responder_image": responder_image
        }
        return data


class ReportToOrganizationUserConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        self.user_id = self.scope['url_route']['kwargs']['pk']
        broadcast_room = f"user_{self.user_id}"
        self.broadcast_room = broadcast_room
        await self.channel_layer.group_add(
            broadcast_room,
            self.channel_name
        )
        await self.send({
            "type": "websocket.accept"
        })

    async def websocket_receive(self, event):  # websocket.receive
        data = event.get("text", None)
        if data:
            user_data = ast.literal_eval(data)
            incident_data = await self.send_user_notification(user_data)
            incident_data = {**user_data, **incident_data}
            incident_data = str(incident_data).replace("'", '"')
            await self.channel_layer.group_send(
                self.broadcast_room,
                {
                    "type": "broadcast_message",
                    "text": str(incident_data)
                }
            )

    async def broadcast_message(self, event):
        await self.send({
            "type": "websocket.send",
            "text": event['text']
        })

    async def websocket_disconnect(self, event):
        print('disconnect', event)

    @database_sync_to_async
    def send_user_notification(self, data):
        incident_id = data['incident_id']
        data = {}
        try:

            obj = Incident.objects.get(id=incident_id)
            organizatiion_contact_obj = OrganizationContact.objects.filter(organization_id=obj.organization.id,
                                                                           user_id=self.user_id).first()
            data["uuid"] = str(organizatiion_contact_obj.uuid)
            data["latitude"] = obj.latitude
            data["longitude"] = obj.longitude
            if obj.streaming_id:
                data["streaming_id"] = obj.streaming_id
            else:
                data["streaming_id"] = ""
        except:
            obj = False
        return data
