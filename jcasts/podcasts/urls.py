from django.urls import path

from jcasts.podcasts import views

app_name = "podcasts"


urlpatterns = [
    path("", views.index, name="index"),
    path("search/podcasts/", views.search_podcasts, name="search_podcasts"),
    path("search/itunes/", views.search_itunes, name="search_itunes"),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/",
        views.podcast_detail,
        name="podcast_detail",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/episodes/",
        views.episodes,
        name="podcast_episodes",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/similar/",
        views.similar,
        name="podcast_similar",
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
    path(
        "discover/",
        views.category_list,
        name="category_list",
    ),
    path(
        "discover/<int:category_id>/<slug:slug>/",
        views.category_detail,
        name="category_detail",
    ),
]
