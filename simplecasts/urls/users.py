from django.urls import path

from simplecasts.views import users

app_name = "users"

urlpatterns = [
    path("preferences/", users.user_preferences, name="preferences"),
    path("stats/", users.user_stats, name="stats"),
    path(
        "feeds/",
        users.import_podcast_feeds,
        name="import_podcast_feeds",
    ),
    path(
        "feeds/export/",
        users.export_podcast_feeds,
        name="export_podcast_feeds",
    ),
    path("delete/", users.delete_account, name="delete_account"),
    path("unsubscribe/", users.unsubscribe, name="unsubscribe"),
]
