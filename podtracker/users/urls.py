from django.urls import path

from podtracker.users import views

app_name = "users"

urlpatterns = [
    path("account/preferences/", views.user_preferences, name="preferences"),
    path("account/stats/", views.user_stats, name="stats"),
    path("account/export/", views.export_podcast_feeds, name="export_podcast_feeds"),
    path(
        "account/export/csv/",
        views.export_podcast_feeds_csv,
        name="export_podcast_feeds_csv",
    ),
    path(
        "account/export/json/",
        views.export_podcast_feeds_json,
        name="export_podcast_feeds_json",
    ),
    path(
        "account/export/opml/",
        views.export_podcast_feeds_opml,
        name="export_podcast_feeds_opml",
    ),
    path("account/delete/", views.delete_account, name="delete_account"),
]
