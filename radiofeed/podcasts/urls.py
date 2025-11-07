from django.urls import path, register_converter

from radiofeed.podcasts import views

app_name = "podcasts"


class _SignedIntConverter:
    regex = r"-?\d+"  # allow optional leading '-'

    def to_python(self, value: str) -> int:
        return int(value)

    def to_url(self, value: int) -> str:
        return str(value)


register_converter(_SignedIntConverter, "sint")

urlpatterns = [
    path("subscriptions/", views.subscriptions, name="subscriptions"),
    path("discover/", views.discover, name="discover"),
    path("search/", views.search_podcasts, name="search_podcasts"),
    path("search/itunes/", views.search_itunes, name="search_itunes"),
    path(
        "podcasts/<slug:slug>-<int:podcast_id>/",
        views.podcast_detail,
        name="podcast_detail",
    ),
    path(
        "podcasts/<slug:slug>-<int:podcast_id>/episodes/",
        views.episodes,
        name="episodes",
    ),
    path(
        "podcasts/<slug:slug>-<int:podcast_id>/season/<sint:season>/",
        views.season,
        name="season",
    ),
    path(
        "podcasts/<slug:slug>-<int:podcast_id>/similar/",
        views.similar,
        name="similar",
    ),
    path(
        "podcasts/<int:podcast_id>/latest-episode/",
        views.latest_episode,
        name="latest_episode",
    ),
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
