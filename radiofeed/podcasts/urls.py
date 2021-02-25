from django.urls import path

from .views import categories, list_detail

app_name = "podcasts"

urlpatterns = [
    path("podcasts/", list_detail.index, name="index"),
    path("search/podcasts/", list_detail.search_podcasts, name="search_podcasts"),
    path("search/itunes/", list_detail.search_itunes, name="search_itunes"),
    path(
        "podcasts/<int:podcast_id>/actions/",
        list_detail.podcast_actions,
        name="actions",
    ),
    path(
        "podcasts/<int:podcast_id>/cover-image/",
        list_detail.podcast_cover_image,
        name="podcast_cover_image",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/similar/",
        list_detail.recommendations,
        name="podcast_recommendations",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/about/",
        list_detail.about,
        name="podcast_detail",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/",
        list_detail.episodes,
        name="podcast_episodes",
    ),
    path(
        "podcasts/<int:podcast_id>/~subscribe/",
        list_detail.subscribe,
        name="subscribe",
    ),
    path(
        "podcasts/<int:podcast_id>/~unsubscribe/",
        list_detail.unsubscribe,
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
