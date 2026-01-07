from django.urls import path

from simplecasts.views import users

app_name = "users"

urlpatterns = [
    path("account/preferences/", users.user_preferences, name="preferences"),
    path("account/stats/", users.user_stats, name="stats"),
    path(
        "account/feeds/",
        users.import_podcast_feeds,
        name="import_podcast_feeds",
    ),
    path(
        "account/feeds/export/",
        users.export_podcast_feeds,
        name="export_podcast_feeds",
    ),
    path("account/delete/", users.delete_account, name="delete_account"),
    path("unsubscribe/", users.unsubscribe, name="unsubscribe"),
]
