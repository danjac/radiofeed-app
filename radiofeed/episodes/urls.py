# Django
from django.urls import path

# Local
from . import views

app_name = "episodes"

urlpatterns = [
    path("new/", views.episode_list, name="episode_list"),
    path("search/episodes/", views.search_episodes, name="search_episodes"),
    path("player/<int:episode_id>/~start/", views.toggle_player, name="start_player"),
    path("player/~start/", views.toggle_player, name="stop_player"),
    path("player/~next/", views.toggle_player, name="play_next_episode"),
    path("player/~timeupdate/", views.player_timeupdate, name="player_timeupdate"),
    path("history/", views.history, name="history"),
    path(
        "history/<int:episode_id>/~remove/",
        views.remove_history,
        name="remove_history",
    ),
    path("bookmarks/", views.bookmark_list, name="bookmark_list"),
    path("bookmarks/<int:episode_id>/~add/", views.add_bookmark, name="add_bookmark"),
    path(
        "bookmarks/<int:episode_id>/~remove/",
        views.remove_bookmark,
        name="remove_bookmark",
    ),
    path("queue/", views.queue, name="queue"),
    path("queue/~move/", views.move_queue_items, name="move_queue_items"),
    path("queue/<int:episode_id>/~add/", views.add_to_queue, name="add_to_queue"),
    path(
        "queue/<int:episode_id>/~remove/",
        views.remove_from_queue,
        name="remove_from_queue",
    ),
    path("episodes/<int:episode_id>/actions/", views.episode_actions, name="actions"),
    path(
        "episodes/<int:episode_id>/bookmarks/actions/",
        views.episode_actions,
        name="bookmark_actions",
        kwargs={"allow_bookmarks": False},
    ),
    path(
        "episodes/<int:episode_id>/queue/actions/",
        views.episode_actions,
        name="queue_actions",
        kwargs={"allow_queue": False},
    ),
    path(
        "episodes/<int:episode_id>/<slug:slug>/",
        views.episode_detail,
        name="episode_detail",
    ),
]
