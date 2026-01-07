from django.urls import path

from simplecasts.views import bookmarks

app_name = "bookmarks"


urlpatterns = [
    path("bookmarks/", bookmarks.bookmarks, name="bookmarks"),
    path(
        "bookmarks/<int:episode_id>/add/",
        bookmarks.add_bookmark,
        name="add_bookmark",
    ),
    path(
        "bookmarks/<int:episode_id>/remove/",
        bookmarks.remove_bookmark,
        name="remove_bookmark",
    ),
]
