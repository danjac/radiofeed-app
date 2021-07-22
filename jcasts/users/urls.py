from django.urls import include, path

from jcasts.users import views

app_name = "episodes"

urlpatterns = [
    path("preferences/", views.user_preferences, name="user_preferences"),
    path("stats/", views.user_stats, name="user_stats"),
    path("~export/", views.export_podcast_feeds, name="export_podcast_feeds"),
    path("~delete/", views.delete_account, name="delete_account"),
    path("", include("allauth.urls")),
]
