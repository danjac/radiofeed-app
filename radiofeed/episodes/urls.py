from django.urls import path

from .views import episodes, favorites, history, player, queue

app_name = "episodes"


urlpatterns = [
    path("new/", episodes.index, name="index"),
    path("search/episodes/", episodes.search_episodes, name="search_episodes"),
    path(
        "episodes/<int:episode_id>/actions/", episodes.episode_actions, name="actions"
    ),
    path(
        "episodes/<int:episode_id>/<slug:slug>/",
        episodes.episode_detail,
        name="episode_detail",
    ),
    path(
        "player/<int:episode_id>/~start/",
        player.start_player,
        name="start_player",
    ),
    path(
        "player/~start/",
        player.stop_player,
        name="stop_player",
    ),
    path(
        "player/~next/",
        player.play_next_episode,
        name="play_next_episode",
    ),
    path("player/~timeupdate/", player.player_timeupdate, name="player_timeupdate"),
    path("history/", history.index, name="history"),
    path(
        "history/<int:episode_id>/~remove/",
        history.remove_history,
        name="remove_history",
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
    path("queue/<int:episode_id>/~add/", queue.add_to_queue, name="add_to_queue"),
    path(
        "queue/<int:episode_id>/~remove/",
        queue.remove_from_queue,
        name="remove_from_queue",
    ),
]
