# Django
from django.urls import path

# Local
from . import views

app_name = "episodes"

urlpatterns = [
    path("", views.episode_list, name="episode_list"),
    path("player/<int:episode_id>/~start/", views.start_player, name="start_player"),
    path("player/~stop/", views.stop_player, name="stop_player"),
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
