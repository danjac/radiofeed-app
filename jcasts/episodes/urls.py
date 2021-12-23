from django.urls import path

from jcasts.episodes.views import (
    bookmarks,
    episode_detail,
    history,
    index,
    player,
    search_episodes,
)

app_name = "episodes"


urlpatterns = [
    path("new/", index, name="index"),
    path("search/episodes/", search_episodes, name="search_episodes"),
    path(
        "episodes/<int:episode_id>/<slug:slug>/",
        episode_detail,
        name="episode_detail",
    ),
    path("player/~reload/", player.reload_player, name="reload_player"),
    path(
        "player/<int:episode_id>/~start/",
        player.start_player,
        name="start_player",
    ),
    path(
        "player/~close/",
        player.close_player,
        name="close_player",
    ),
    path(
        "player/~complete/",
        player.close_player,
        name="player_complete",
        kwargs={
            "mark_complete": True,
        },
    ),
    path(
        "player/~timeupdate/",
        player.player_time_update,
        name="player_time_update",
    ),
    path("history/", history.index, name="history"),
    path(
        "history/<int:episode_id>/~complete/",
        history.mark_complete,
        name="mark_complete",
    ),
    path(
        "history/<int:episode_id>/~remove/",
        history.remove_audio_log,
        name="remove_audio_log",
    ),
    path("bookmarks/", bookmarks.index, name="bookmarks"),
    path(
        "bookmarks/<int:episode_id>/~add/",
        bookmarks.add_bookmark,
        name="add_bookmark",
    ),
    path(
        "bookmarks/<int:episode_id>/~remove/",
        bookmarks.remove_bookmark,
        name="remove_bookmark",
    ),
]
