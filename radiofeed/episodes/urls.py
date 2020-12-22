# Django
from django.urls import path

# Local
from . import views

app_name = "episodes"

urlpatterns = [
    path("", views.episode_list, name="episode_list"),
    path("player/<int:episode_id>/~start/", views.start_player, name="start_player"),
    path(
        "player/~pause/",
        views.toggle_player_pause,
        name="pause_player",
        kwargs={"pause": True},
    ),
    path(
        "player/~resume/",
        views.toggle_player_pause,
        name="resume_player",
        kwargs={"pause": False},
    ),
    path("player/~stop/", views.stop_player, name="stop_player"),
    path(
        "player/~mark-complete/",
        views.stop_player,
        name="mark_complete",
        kwargs={"completed": True},
    ),
    path("player/~update/", views.update_player_time, name="update_player_time"),
    path("history/", views.history, name="history"),
    path("bookmarks/", views.bookmark_list, name="bookmark_list"),
    path("bookmarks/<int:episode_id>/~add/", views.add_bookmark, name="add_bookmark"),
    path(
        "bookmarks/<int:episode_id>/~remove/",
        views.remove_bookmark,
        name="remove_bookmark",
    ),
    path("<int:episode_id>/<slug:slug>/", views.episode_detail, name="episode_detail"),
]
