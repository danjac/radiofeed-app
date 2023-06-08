from django.urls import path

from radiofeed.websub import views

app_name = "websub"
urlpatterns = [
    path("websub/<int:subscription_id>/", views.callback, name="callback"),
]
