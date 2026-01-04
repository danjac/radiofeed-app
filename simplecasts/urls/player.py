from django.urls import path

from simplecasts.views import player

app_name = "player"


urlpatterns = [
    path(
        "start/<int:episode_id>/",
        player.start_player,
        name="start",
    ),
    path(
        "close/",
        player.close_player,
        name="close",
    ),
    path(
        "time-update/",
        player.player_time_update,
        name="time_update",
    ),
]
