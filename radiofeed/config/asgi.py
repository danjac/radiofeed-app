# Standard Library
import os

# Django
import django
from django.core.asgi import get_asgi_application  # noqa
from django.urls import re_path  # noqa

# Third Party Libraries
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa
from channels.sessions import SessionMiddlewareStack  # noqa

# RadioFeed
from radiofeed.episodes.consumers import PlayerConsumer

django.setup()  # noqa


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "radiofeed.config.settings.local")


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
