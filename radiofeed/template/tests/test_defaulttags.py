from django.urls import reverse

from radiofeed.podcasts.models import Category

from ..defaulttags import (
    active_link,
    htmlattrs,
    jsonify,
    keepspaces,
    percent,
    share_buttons,
)


class TestHtmlAttrs:
    def test_empty_dict(self):
        assert htmlattrs({}) == ""

    def test_attrs(self):
        assert (
            htmlattrs({"data_action": "submit", "type": "button"})
            == 'data-action="submit" type="button"'
        )


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
        route = active_link({"request": req}, "podcasts:index")
        assert route.url == reverse("podcasts:index")
        assert not route.match
        assert not route.exact

    def test_active_link_non_exact_match(self, rf):
        url = Category(id=1234, name="test").get_absolute_url()
        req = rf.get(url)
        route = active_link({"request": req}, "podcasts:categories")
        assert route.url == reverse("podcasts:categories")
        assert route.match
        assert not route.exact

    def test_active_link_exact_match(self, rf):
        url = reverse("podcasts:index")
        req = rf.get(url)
        route = active_link({"request": req}, "podcasts:index")
        assert route.url == reverse("podcasts:index")
        assert route.match
        assert route.exact


class TestKeepspaces:
    def test_value_is_none(self):
        return keepspaces(None) == ""

    def test_value_has_html(self):
        return keepspaces("test<br />this<ul><li>hello</li></ul>") == "test this hello"
