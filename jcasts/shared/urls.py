from django.urls import path

from jcasts.shared.views import home_page, robots, credits, shortcuts, privacy

urlpatterns = [
    path("", home_page),
    path("/robots.txt", robots),
    path("/about/credits/", credits),
    path("/about/shortcuts/", shortcuts),
    path("/about/privacy/", privacy),
]
