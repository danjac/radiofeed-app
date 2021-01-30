# Django
from django.urls import path

# Local
from . import views

app_name = "podcasts"

urlpatterns = [
    path("", views.landing_page, name="landing_page"),
    path("podcasts/", views.podcast_list, name="podcast_list"),
    path("podcasts/<int:podcast_id>/actions/", views.podcast_actions, name="actions"),
    path("podcasts/<int:podcast_id>/~subscribe/", views.subscribe, name="subscribe"),
    path(
        "podcasts/<int:podcast_id>/~unsubscribe/", views.unsubscribe, name="unsubscribe"
    ),
    path(
        "podcasts/<int:podcast_id>/cover-image/",
        views.podcast_cover_image,
        name="podcast_cover_image",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/",
        views.podcast_episode_list,
        name="podcast_episode_list",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/similar/",
        views.podcast_recommendations,
        name="podcast_recommendations",
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/about/",
        views.podcast_detail,
        name="podcast_detail",
    ),
    path("itunes/", views.search_itunes, name="search_itunes"),
    path("discover/", views.category_list, name="category_list"),
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
