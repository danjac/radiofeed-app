# Django
from django.urls import path

# Local
from . import views

app_name = "podcasts"

urlpatterns = [
    path("", views.podcast_list, name="podcast_list"),
    path("itunes/", views.search_itunes, name="search_itunes"),
    path("itunes/~add/", views.add_podcast, name="add_podcast"),
    path("categories/", views.category_list, name="category_list"),
    path(
        "categories/<int:category_id>/itunes/",
        views.itunes_category,
        name="itunes_category",
    ),
    path(
        "categories/<int:category_id>/<slug:slug>/",
        views.category_detail,
        name="category_detail",
    ),
    path("<int:podcast_id>/subscribe/", views.subscribe, name="subscribe"),
    path("<int:podcast_id>/unsubscribe/", views.unsubscribe, name="unsubscribe"),
    path("<int:podcast_id>/<slug:slug>/", views.podcast_detail, name="podcast_detail"),
]
