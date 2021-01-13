# Django
from django.urls import reverse

# RadioFeed
from radiofeed.podcasts.models import Podcast

# Local
from ..defaulttags import active_link


class TestActiveLink:
    def test_active_link_no_match(self, rf):
        url = reverse("account_login")
        req = rf.get(url)
        route = active_link({"request": req}, "podcasts:podcast_list")
        assert route.url == reverse("podcasts:podcast_list")
        assert not route.match
        assert not route.exact

    def test_active_link_non_exact_match(self, rf):
        podcast = Podcast(id=1234, title="hello")
        url = podcast.get_absolute_url()
        req = rf.get(url)
        route = active_link({"request": req}, "podcasts:podcast_list")
        assert route.url == reverse("podcasts:podcast_list")
        assert route.match
        assert not route.exact

    def test_active_link_exact_match(self, rf):
        url = reverse("podcasts:podcast_list")
        req = rf.get(url)
        route = active_link({"request": req}, "podcasts:podcast_list")
        assert route.url == reverse("podcasts:podcast_list")
        assert route.match
        assert route.exact
