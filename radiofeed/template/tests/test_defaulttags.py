from django.urls import reverse

from radiofeed.podcasts.models import Podcast

from ..defaulttags import active_link, jsonify, keepspaces, percent, share_buttons, svg


class TestJsonify:
    def test_jsonify(self):
        assert jsonify({"title": "test"}) == '{"title": "test"}'


class TestPercent:
    def test_if_either_none(self):
        assert percent(10, 0) == 0
        assert percent(0, 10) == 0
        assert percent(0, 0) == 0
        assert percent(None, None) == 0

    def test_percent(self):
        assert percent(30, 60) == 50


class TestShareButtons:
    def test_share(self, rf):
        url = "/podcasts/1234/test/"
        share_urls = share_buttons({"request": rf.get(url)}, url, "Test Podcast")[
            "share_urls"
        ]

        assert (
            share_urls["email"]
            == "mailto:?subject=Test%20Podcast&body=http%3A//testserver/podcasts/1234/test/"
        )

        assert (
            share_urls["facebook"]
            == "https://www.facebook.com/sharer/sharer.php?u=http%3A//testserver/podcasts/1234/test/"
        )

        assert (
            share_urls["twitter"]
            == "https://twitter.com/share?url=http%3A//testserver/podcasts/1234/test/&text=Test%20Podcast"
        )

        assert (
            share_urls["linkedin"]
            == "https://www.linkedin.com/sharing/share-offsite/?url=http%3A//testserver/podcasts/1234/test/"
        )


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


class TestKeepspaces:
    def test_value_is_none(self):
        return keepspaces(None) == ""

    def test_value_has_html(self):
        return keepspaces("test<br />this<ul><li>hello</li></ul>") == "test this hello"


class TestSvg:
    def test_render_svg(self):
        result = svg("ellipsis", css_class="h-4 w-4")
        assert 'class="h-4 w-4"' in result
