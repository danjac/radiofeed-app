from django.urls import path

from jcasts.podcasts import views

app_name = "podcasts"


urlpatterns = [
    path("", views.index, name="index"),
    path("search/podcasts/", views.search_podcasts, name="search_podcasts"),
    path("search/autocomplete/", views.search_autocomplete, name="search_autocomplete"),
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
        views.recommendations,
        name="podcast_recommendations",
    ),
    path(
        "podcasts/<int:podcast_id>/~latest/",
        views.latest,
        name="latest",
    ),
    path(
        "podcasts/<int:podcast_id>/~follow/",
        views.follow,
        name="follow",
    ),
    path(
        "podcasts/<int:podcast_id>/~unfollow/",
        views.unfollow,
        name="unfollow",
    ),
    path(
        "discover/<int:category_id>/<slug:slug>/",
        views.category_detail,
        name="category_detail",
    ),
]
