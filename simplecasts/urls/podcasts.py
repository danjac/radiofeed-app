from django.urls import path, register_converter

from simplecasts.views import podcasts

app_name = "podcasts"


class _SignedIntConverter:
    regex = r"-?\d+"  # allow optional leading '-'

    def to_python(self, value: str) -> int:
        return int(value)

    def to_url(self, value: int) -> str:
        return str(value)


register_converter(_SignedIntConverter, "sint")

urlpatterns = [
    path("subscriptions/", podcasts.subscriptions, name="subscriptions"),
    path("discover/", podcasts.discover, name="discover"),
    path("private-feeds/", podcasts.private_feeds, name="private_feeds"),
    path(
        "private-feeds/new/",
        podcasts.add_private_feed,
        name="add_private_feed",
    ),
    path(
        "private-feeds/<int:podcast_id>/remove/",
        podcasts.remove_private_feed,
        name="remove_private_feed",
    ),
    path(
        "podcasts/<slug:slug>-<int:podcast_id>/",
        podcasts.podcast_detail,
        name="detail",
    ),
    path(
        "podcasts/<slug:slug>-<int:podcast_id>/episodes/",
        podcasts.episodes,
        name="episodes",
    ),
    path(
        "podcasts/<slug:slug>-<int:podcast_id>/season/<sint:season>/",
        podcasts.season,
        name="season",
    ),
    path(
        "podcasts/<slug:slug>-<int:podcast_id>/similar/",
        podcasts.similar,
        name="similar",
    ),
    path(
        "podcasts/<int:podcast_id>/latest-episode/",
        podcasts.latest_episode,
        name="latest_episode",
    ),
    path(
        "podcasts/<int:podcast_id>/subscribe/",
        podcasts.subscribe,
        name="subscribe",
    ),
    path(
        "podcasts/<int:podcast_id>/unsubscribe/",
        podcasts.unsubscribe,
        name="unsubscribe",
    ),
    path("search/podcasts/", podcasts.search_podcasts, name="search_podcasts"),
    path("search/itunes/", podcasts.search_itunes, name="search_itunes"),
    path("search/people/", podcasts.search_people, name="search_people"),
]
