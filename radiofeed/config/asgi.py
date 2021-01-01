# Django
from django.core.asgi import get_asgi_application
from django.urls import re_path

# Third Party Libraries
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.sessions import SessionMiddlewareStack

# RadioFeed
from radiofeed.episodes.consumers import PlayerConsumer

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": SessionMiddlewareStack(
            URLRouter(
                [re_path(r"ws/player/(?P<episode_id>\d+)/$", PlayerConsumer.as_asgi())]
            )
        ),
    }
)
