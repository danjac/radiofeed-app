from django.urls import path

from simplecasts.users import views

app_name = "users"

urlpatterns = [
    path("account/preferences/", views.user_preferences, name="preferences"),
    path("account/stats/", views.user_stats, name="stats"),
    path(
        "account/feeds/",
        views.import_podcast_feeds,
        name="import_podcast_feeds",
    ),
    path(
        "account/feeds/export/",
        views.export_podcast_feeds,
        name="export_podcast_feeds",
    ),
    path("account/delete/", views.delete_account, name="delete_account"),
    path("unsubscribe/", views.unsubscribe, name="unsubscribe"),
]
