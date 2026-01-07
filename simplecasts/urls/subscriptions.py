from django.urls import path

from simplecasts.views import subscriptions

app_name = "subscriptions"


urlpatterns = [
    path("subscriptions/", subscriptions.subscriptions, name="subscriptions"),
    path(
        "podcasts/<int:podcast_id>/subscribe/",
        subscriptions.subscribe,
        name="subscribe",
    ),
    path(
        "podcasts/<int:podcast_id>/unsubscribe/",
        subscriptions.unsubscribe,
        name="unsubscribe",
    ),
]
