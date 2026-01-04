from django.urls import path

from simplecasts.views import bookmarks

app_name = "bookmarks"

urlpatterns = [
    path("", bookmarks.index, name="index"),
    path(
        "<int:episode_id>/add/",
        bookmarks.add_bookmark,
        name="add",
    ),
    path(
        "<int:episode_id>/remove/",
        bookmarks.remove_bookmark,
        name="remove",
    ),
]
