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
    path(
        "account/private-feeds/",
        views.private_feeds,
        name="private_feeds",
    ),
    path(
        "account/private-feeds/new/",
        views.add_private_feed,
        name="add_private_feed",
    ),
    path(
        "account/private-feeds/remove/<int:podcast_id>/",
        views.remove_private_feed,
        name="remove_private_feed",
    ),
    path("account/delete/", views.delete_account, name="delete_account"),
]
