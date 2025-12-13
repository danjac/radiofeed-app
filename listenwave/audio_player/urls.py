from django.urls import path

from listenwave.audio_player import views

app_name = "audio_player"


urlpatterns = [
    path(
        "player-time-update/",
        views.player_time_update,
        name="player_time_update",
    ),
]
