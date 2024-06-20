from django.urls import path

from radiofeed.users import views

app_name = "users"

urlpatterns = [
    path("account/preferences/", views.user_preferences, name="preferences"),
    path("account/stats/", views.user_stats, name="stats"),
    path(
        "account/feeds/",
        views.manage_podcast_feeds,
        name="manage_podcast_feeds",
    ),
    path(
        "account/feeds/export/",
        views.export_podcast_feeds,
        name="export_podcast_feeds",
    ),
    path(
        "account/feeds/import/",
        views.import_podcast_feeds,
        name="import_podcast_feeds",
    ),
    path("account/delete/", views.delete_account, name="delete_account"),
]
