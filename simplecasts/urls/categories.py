from django.urls import path

from simplecasts.views import categories

app_name = "categories"

urlpatterns = [
    path("", categories.index, name="index"),
    path("<slug:slug>/", categories.detail, name="detail"),
]
