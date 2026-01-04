from django.urls import path

from simplecasts.views import search

app_name = "search"

urlpatterns = [
    path("episodes/", search.search_episodes, name="episodes"),
    path("podcasts/", search.search_podcasts, name="podcasts"),
    path("people/", search.search_people, name="people"),
    path("itunes/", search.search_itunes, name="itunes"),
]
