from django.urls import path

from radiofeed.podcasts import views

app_name = "podcasts"


urlpatterns = [
    path("", views.index, name="index"),
    path("search/podcasts/", views.search_podcasts, name="search_podcasts"),
    path("search/itunes/", views.search_itunes, name="search_itunes"),
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
        "podcasts/<int:podcast_id>/<slug:slug>/",
        views.podcast_detail,
        name="podcast_detail",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/latest/",
        views.latest_episode,
        name="latest_episode",
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
        "categories/",
        views.category_list,
        name="category_list",
    ),
    path(
        "categories/<int:category_id>/<slug:slug>/",
        views.category_detail,
        name="category_detail",
    ),
]
