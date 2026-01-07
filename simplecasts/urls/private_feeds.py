from django.urls import path

from simplecasts.views import private_feeds

app_name = "private_feeds"


urlpatterns = [
    path("private-feeds/", private_feeds.private_feeds, name="private_feeds"),
    path(
        "private-feeds/new/",
        private_feeds.add_private_feed,
        name="add_private_feed",
    ),
    path(
        "private-feeds/<int:podcast_id>/remove/",
        private_feeds.remove_private_feed,
        name="remove_private_feed",
    ),
]
