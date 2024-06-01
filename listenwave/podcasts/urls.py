from django.urls import path

from listenwave.podcasts import views

app_name = "podcasts"

urlpatterns = [
    path("", views.index, name="index"),
    path("podcasts/", views.subscriptions, name="subscriptions"),
    path("discover/", views.discover, name="discover"),
    path(
        "podcasts/<slug:slug>-<int:podcast_id>/",
        views.podcast_detail,
        name="podcast_detail",
    ),
    path(
        "podcasts/<slug:slug>-<int:podcast_id>/latest/",
        views.latest_episode,
        name="latest_episode",
    ),
    path(
        "podcasts/<slug:slug>-<int:podcast_id>/episodes/",
        views.episodes,
        name="podcast_episodes",
    ),
    path(
        "podcasts/<slug:slug>-<int:podcast_id>/similar/",
        views.similar,
        name="podcast_similar",
    ),
    path("itunes/", views.search_itunes, name="search_itunes"),
    path(
        "subscribe/<int:podcast_id>/",
        views.subscribe,
        name="subscribe",
    ),
    path(
        "unsubscribe/<int:podcast_id>/",
        views.unsubscribe,
        name="unsubscribe",
    ),
    path(
        "categories/",
        views.category_list,
        name="category_list",
    ),
    path(
        "categories/<slug:slug>-<int:category_id>/",
        views.category_detail,
        name="category_detail",
    ),
    path(
        "private-feeds/",
        views.private_feeds,
        name="private_feeds",
    ),
    path(
        "private-feeds/new/",
        views.add_private_feed,
        name="add_private_feed",
    ),
    path(
        "private-feeds/remove/<int:podcast_id>/",
        views.remove_private_feed,
        name="remove_private_feed",
    ),
]
