from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter, ChannelNameRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator, OriginValidator

from apps.incident.consumers import ReportLocationConsumer, ReportToOrganizationUserConsumer

application = ProtocolTypeRouter({

    'websocket': AllowedHostsOriginValidator(
        URLRouter(
            [
                # url(r"chat/", ChatConsumer, name='chat')
                path('wss/<int:pk>/incident/', ReportLocationConsumer, name='location-update'),
                path('wss/<int:pk>/organization-owner/', ReportToOrganizationUserConsumer,
                     name='organization-owner-notification'),
            ]
        ),
    ),
})
