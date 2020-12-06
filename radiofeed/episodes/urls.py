# Django
from django.urls import path

# Local
from . import views

app_name = "episodes"

urlpatterns = [
    path("", views.episode_list, name="episode_list"),
    path("<int:episode_id>/~play/", views.play_episode, name="play_episode"),
    path("<int:episode_id>/~stop/", views.stop_episode, name="stop_episode"),
    path(
        "<int:episode_id>/~progress/", views.episode_progress, name="episode_progress"
    ),
    path("<int:episode_id>/<slug:slug>/", views.episode_detail, name="episode_detail"),
]
