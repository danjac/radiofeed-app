from django.urls import include, path

from . import views

urlpatterns = [
    path("preferences/", views.user_preferences, name="user_preferences"),
    path("stats/", views.user_stats, name="user_stats"),
    path("~delete/", views.delete_account, name="delete_account"),
    path("", include("turbo_allauth.urls")),
]
