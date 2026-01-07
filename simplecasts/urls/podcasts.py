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
    path("discover/", podcasts.discover, name="discover"),
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
    path("search/podcasts/", podcasts.search_podcasts, name="search_podcasts"),
    path("search/itunes/", podcasts.search_itunes, name="search_itunes"),
    path("search/people/", podcasts.search_people, name="search_people"),
]
