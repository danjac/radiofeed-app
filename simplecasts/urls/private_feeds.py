from django.urls import path

from simplecasts.views import private_feeds

app_name = "private_feeds"

urlpatterns = [
    path(
        "",
        private_feeds.index,
        name="index",
    ),
    path(
        "new/",
        private_feeds.add_private_feed,
        name="add",
    ),
    path(
        "<int:podcast_id>/remove/",
        private_feeds.remove_private_feed,
        name="remove",
    ),
]
