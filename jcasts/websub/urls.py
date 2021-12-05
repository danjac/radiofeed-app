from django.urls import path

from jcasts.websub import views

app_name = "websub"


urlpatterns = [
    path("websub/<uuid:subscription_id>/", views.websub_callback, name="callback"),
]
