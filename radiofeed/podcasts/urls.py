# Django
from django.urls import path

# Local
from . import views

app_name = "podcasts"

urlpatterns = [
    path("", views.podcast_list, name="podcast_list"),
    path("<int:podcast_id>/<slug:slug>/", views.podcast_detail, name="podcast_detail"),
]
