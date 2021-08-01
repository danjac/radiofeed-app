from django.urls import path

from jcasts.episodes.views import (
    actions,
    episode_detail,
    favorites,
    history,
    index,
    player,
    queue,
    search_episodes,
)

app_name = "episodes"


urlpatterns = [
    path("new/", index, name="index"),
    path("featured/", index, name="featured", kwargs={"featured": True}),
    path("search/episodes/", search_episodes, name="search_episodes"),
    path(
        "episodes/actions/<int:episode_id>/",
        actions,
        name="actions",
    ),
    path(
        "episodes/<int:episode_id>/<slug:slug>/",
        episode_detail,
        name="episode_detail",
    ),
    path("player/", player.get_player, name="get_player"),
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
        "player/~done/",
        player.mark_complete,
        name="mark_complete",
    ),
    path(
        "player/~timeupdate/",
        player.player_time_update,
        name="player_time_update",
    ),
    path("history/", history.index, name="history"),
    path(
        "history/<int:episode_id>/~remove/",
        history.remove_audio_log,
        name="remove_audio_log",
    ),
    path("favorites/", favorites.index, name="favorites"),
    path(
        "favorites/<int:episode_id>/~add/",
        favorites.add_favorite,
        name="add_favorite",
    ),
    path(
        "favorites/<int:episode_id>/~remove/",
        favorites.remove_favorite,
        name="remove_favorite",
    ),
    path("queue/", queue.index, name="queue"),
    path("queue/~move/", queue.move_queue_items, name="move_queue_items"),
    path(
        "queue/<int:episode_id>/~add-start/",
        queue.add_to_queue,
        name="add_to_queue_start",
        kwargs={"to": "start"},
    ),
    path(
        "queue/<int:episode_id>/~add-end/",
        queue.add_to_queue,
        name="add_to_queue_end",
        kwargs={"to": "end"},
    ),
    path(
        "queue/<int:episode_id>/~remove/",
        queue.remove_from_queue,
        name="remove_from_queue",
    ),
]
