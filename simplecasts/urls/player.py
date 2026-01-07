from django.urls import path

from simplecasts.views import player

app_name = "player"


urlpatterns = [
    path("player/start/<int:episode_id>/", player.start_player, name="start_player"),
    path("player/close/", player.close_player, name="close_player"),
    path("player/time-update/", player.player_time_update, name="player_time_update"),
]
