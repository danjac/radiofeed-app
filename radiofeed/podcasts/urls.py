from django.urls import path

from .views import categories, detail, podcasts

app_name = "podcasts"

urlpatterns = [
    path("podcasts/", podcasts.index, name="index"),
    path("search/podcasts/", podcasts.search_podcasts, name="search_podcasts"),
    path("search/itunes/", podcasts.search_itunes, name="search_itunes"),
    path("podcasts/<int:podcast_id>/actions/", detail.podcast_actions, name="actions"),
    path(
        "podcasts/<int:podcast_id>/cover-image/",
        detail.podcast_cover_image,
        name="podcast_cover_image",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/similar/",
        detail.recommendations,
        name="podcast_recommendations",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/about/",
        detail.about,
        name="podcast_detail",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/",
        detail.episodes,
        name="podcast_episodes",
    ),
    path(
        "podcasts/<int:podcast_id>/~subscribe/",
        detail.subscribe,
        name="subscribe",
    ),
    path(
        "podcasts/<int:podcast_id>/~unsubscribe/",
        detail.unsubscribe,
        name="unsubscribe",
    ),
    path("discover/", categories.index, name="categories"),
    path(
        "discover/<int:category_id>/itunes/",
        categories.itunes_category,
        name="itunes_category",
    ),
    path(
        "discover/<int:category_id>/<slug:slug>/",
        categories.category_detail,
        name="category_detail",
    ),
]
