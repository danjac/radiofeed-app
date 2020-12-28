# Django
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver


def close_player(sender, user, request, **kwargs):
    # removes current player from session
    request.session.pop("player", None)


receiver(user_logged_in)(close_player)
receiver(user_logged_out)(close_player)
