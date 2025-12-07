from django.urls import path

from listenwave.episodes import views

app_name = "episodes"


urlpatterns = [
    path("new/", views.index, name="index"),
    path("search/episodes/", views.search_episodes, name="search_episodes"),
    path(
        "episodes/<slug:slug>-<int:episode_id>/",
        views.episode_detail,
        name="episode_detail",
    ),
    path(
        "player/start/<int:episode_id>/",
        views.start_player,
        name="start_player",
    ),
    path(
        "player/close/",
        views.close_player,
        name="close_player",
    ),
    path(
        "player/timeupdate/",
        views.player_time_update,
        name="player_time_update",
    ),
    path("history/", views.history, name="history"),
    path(
        "history/<int:episode_id>/complete/",
        views.mark_audio_log_complete,
        name="mark_audio_log_complete",
    ),
    path(
        "history/<int:episode_id>/remove/",
        views.remove_audio_log,
        name="remove_audio_log",
    ),
    path("bookmarks/", views.bookmarks, name="bookmarks"),
    path(
        "bookmarks/<int:episode_id>/add/",
        views.add_bookmark,
        name="add_bookmark",
    ),
    path(
        "bookmarks/<int:episode_id>/remove/",
        views.remove_bookmark,
        name="remove_bookmark",
    ),
]
