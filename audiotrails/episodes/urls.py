from django.urls import path

from . import views

app_name = "episodes"


urlpatterns = [
    path("", views.index, name="index"),
    path("search/episodes/", views.search_episodes, name="search_episodes"),
    path(
        "episodes/preview/<int:episode_id>/",
        views.preview,
        name="episode_preview",
    ),
    path(
        "episodes/<int:episode_id>/<slug:slug>/",
        views.episode_detail,
        name="episode_detail",
    ),
    path(
        "player/<int:episode_id>/~start/",
        views.start_player,
        name="start_player",
    ),
    path(
        "player/~stop/",
        views.stop_player,
        name="stop_player",
    ),
    path(
        "player/~next/",
        views.play_next_episode,
        name="play_next_episode",
    ),
    path(
        "player/~timeupdate/",
        views.player_update_current_time,
        name="player_update_current_time",
    ),
    path(
        "player/~playbackrate/",
        views.player_update_playback_rate,
        name="player_update_playback_rate",
    ),
    path("history/", views.history, name="history"),
    path(
        "history/<int:episode_id>/~remove/",
        views.remove_audio_log,
        name="remove_audio_log",
    ),
    path("favorites/", views.favorites, name="favorites"),
    path(
        "favorites/<int:episode_id>/~add/",
        views.add_favorite,
        name="add_favorite",
    ),
    path(
        "favorites/<int:episode_id>/~remove/",
        views.remove_favorite,
        name="remove_favorite",
    ),
    path("queue/", views.queue, name="queue"),
    path("queue/~move/", views.move_queue_items, name="move_queue_items"),
    path("queue/<int:episode_id>/~add/", views.add_to_queue, name="add_to_queue"),
    path(
        "queue/<int:episode_id>/~remove/",
        views.remove_from_queue,
        name="remove_from_queue",
    ),
]
