from typing import Any

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.http import HttpRequest

from audiotrails.shared.types import AnyUser


def close_player(sender: Any, user: AnyUser, request: HttpRequest, **kwargs) -> None:
    # removes current player from session
    request.session.pop("player", None)


receiver(user_logged_in)(close_player)
receiver(user_logged_out)(close_player)
