# Django
from django.urls import path

# Local
from . import views

app_name = "episodes"

urlpatterns = [
    path("", views.episode_list, name="episode_list"),
    path("player/~start/<int:episode_id>/", views.start_player, name="start_player"),
    path("player/~stop/", views.stop_player, name="stop_player"),
    path("player/~update/", views.update_player_time, name="update_player_time"),
    path("<int:episode_id>/<slug:slug>/", views.episode_detail, name="episode_detail"),
]
