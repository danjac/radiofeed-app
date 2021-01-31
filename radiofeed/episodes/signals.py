from typing import Type

from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.http import HttpRequest


def close_player(
    sender: Type[settings.AUTH_USER_MODEL],
    user: settings.AUTH_USER_MODEL,
    request: HttpRequest,
    **kwargs
):
    # removes current player from session
    request.session.pop("player", None)


receiver(user_logged_in)(close_player)
receiver(user_logged_out)(close_player)
