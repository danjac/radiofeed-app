from django.urls import path

from simplecasts.views import episodes

app_name = "episodes"


urlpatterns = [
    path("new/", episodes.index, name="index"),
    path("search/episodes/", episodes.search_episodes, name="search_episodes"),
    path(
        "episodes/<slug:slug>-<int:episode_id>/",
        episodes.episode_detail,
        name="detail",
    ),
]
