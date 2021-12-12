from django.urls import path

from jcasts.users import views

app_name = "users"

urlpatterns = [
    path("account/preferences/", views.user_preferences, name="preferences"),
    path("account/stats/", views.user_stats, name="stats"),
    path("account/~export/", views.export_podcast_feeds, name="export_podcast_feeds"),
    path("account/~autoplay/", views.toggle_autoplay, name="toggle_autoplay"),
    path("account/~delete/", views.delete_account, name="delete_account"),
]
