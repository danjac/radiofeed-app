from django.urls import path

from jcasts.podcasts import views

app_name = "podcasts"


urlpatterns = [
    path("podcasts/", views.index, name="index"),
    path("podcasts/featured/", views.index, name="featured", kwargs={"featured": True}),
    path("search/podcasts/", views.search_podcasts, name="search_podcasts"),
    path("search/itunes/", views.search_itunes, name="search_itunes"),
    path(
        "podcasts/<int:podcast_id>/actions/",
        views.actions,
        name="actions",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/similar/",
        views.recommendations,
        name="podcast_recommendations",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/episodes/",
        views.episodes,
        name="podcast_episodes",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/",
        views.podcast_detail,
        name="podcast_detail",
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
