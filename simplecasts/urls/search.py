from django.urls import path

from simplecasts.views import search

app_name = "search"

urlpatterns = [
    path("people/", search.search_people, name="people"),
]
