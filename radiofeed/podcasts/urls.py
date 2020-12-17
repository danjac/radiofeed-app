# Django
from django.urls import path

# Local
from . import views

app_name = "podcasts"

urlpatterns = [
    path("", views.landing_page, name="landing_page"),
    path("podcasts/", views.podcast_list, name="podcast_list"),
    path("podcasts/<int:podcast_id>/subscribe/", views.subscribe, name="subscribe"),
    path(
        "podcasts/<int:podcast_id>/unsubscribe/", views.unsubscribe, name="unsubscribe"
    ),
    path(
        "podcasts/<int:podcast_id>/<slug:slug>/",
        views.podcast_detail,
        name="podcast_detail",
    ),
    path("itunes/", views.search_itunes, name="search_itunes"),
    path("itunes/~add/", views.add_podcast, name="add_podcast"),
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
