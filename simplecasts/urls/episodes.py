from django.urls import path

from simplecasts.views import episodes

app_name = "episodes"


urlpatterns = [
    path("new/", episodes.index, name="index"),
    path(
        "episodes/<slug:slug>-<int:episode_id>/",
        episodes.detail,
        name="detail",
    ),
    path("search/episodes/", episodes.search_episodes, name="search_episodes"),
]
