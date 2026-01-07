from django.urls import path

from simplecasts.views import episodes

app_name = "episodes"


urlpatterns = [
    path("new/", episodes.index, name="index"),
    path(
        "episodes/<slug:slug>-<int:episode_id>/",
        episodes.detail,
        name="detail",
    ),
    path("search/episodes/", episodes.search_episodes, name="search_episodes"),
    path("history/", episodes.history, name="history"),
    path(
        "history/<int:episode_id>/complete/",
        episodes.mark_complete,
        name="mark_complete",
    ),
    path(
        "history/<int:episode_id>/remove/",
        episodes.remove_audio_log,
        name="remove_audio_log",
    ),
    path("bookmarks/", episodes.bookmarks, name="bookmarks"),
    path("bookmarks/<int:episode_id>/add/", episodes.add_bookmark, name="add_bookmark"),
    path(
        "bookmarks/<int:episode_id>/remove/",
        episodes.remove_bookmark,
        name="remove_bookmark",
    ),
    path("player/start/<int:episode_id>/", episodes.start_player, name="start_player"),
    path("player/close/", episodes.close_player, name="close_player"),
    path("player/time-update/", episodes.player_time_update, name="player_time_update"),
]
