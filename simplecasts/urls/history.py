from django.urls import path

from simplecasts.views import history

app_name = "history"

urlpatterns = [
    path("", history.index, name="index"),
    path("<int:episode_id>/complete/", history.mark_complete, name="mark_complete"),
    path("<int:episode_id>/remove/", history.remove_audio_log, name="remove_audio_log"),
]
