from django.urls import include, path

from jcasts.users import views

urlpatterns = [
    path("~accept_cookies", views.accept_cookies, name="accept_cookies"),
    path("account/preferences/", views.user_preferences, name="user_preferences"),
    path("account/stats/", views.user_stats, name="user_stats"),
    path("account/~export/", views.export_podcast_feeds, name="export_podcast_feeds"),
    path("account/~delete/", views.delete_account, name="delete_account"),
    path("", include("allauth.urls")),
]
