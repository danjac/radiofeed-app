from django.urls import path

from radiofeed.podcasts import views

app_name = "podcasts"

urlpatterns = [
    path("", views.landing_page, name="landing_page"),
    path("podcasts/", views.index, name="index"),
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
        "categories/",
        views.category_list,
        name="category_list",
    ),
    path(
        "categories/<int:category_id>/<slug:slug>/",
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
