from django.urls import path

from simplecasts.views import subscriptions

app_name = "subscriptions"

urlpatterns = [
    path("", subscriptions.index, name="index"),
    path(
        "<int:podcast_id>/subscribe/",
        subscriptions.subscribe,
        name="subscribe",
    ),
    path(
        "<int:podcast_id>/unsubscribe/",
        subscriptions.unsubscribe,
        name="unsubscribe",
    ),
]
