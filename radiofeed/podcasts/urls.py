from django.urls import path

from . import views

app_name = "podcasts"

urlpatterns = [
    path("podcasts/", views.index, name="index"),
    path("search/podcasts/", views.search_podcasts, name="search_podcasts"),
    path("search/itunes/", views.search_itunes, name="search_itunes"),
    path(
        "podcasts/<int:podcast_id>/preview/",
        views.preview,
        name="preview",
    ),
    path(
        "podcasts/<int:podcast_id>/cover-image/",
        views.podcast_cover_image,
        name="podcast_cover_image",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/similar/",
        views.recommendations,
        name="podcast_recommendations",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/about/",
        views.about,
        name="podcast_detail",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/",
        views.episodes,
        name="podcast_episodes",
    ),
    path(
        "podcasts/<int:podcast_id>/~subscribe/",
        views.subscribe,
        name="subscribe",
    ),
    path(
        "podcasts/<int:podcast_id>/~unsubscribe/",
        views.unsubscribe,
        name="unsubscribe",
    ),
    path("discover/", views.categories, name="categories"),
    path(
        "discover/<int:category_id>/itunes/",
        views.itunes_category,
        name="itunes_category",
    ),
    path(
        "discover/<int:category_id>/<slug:slug>/",
        views.category_detail,
        name="category_detail",
    ),
]
