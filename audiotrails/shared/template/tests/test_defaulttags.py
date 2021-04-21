from django.urls import reverse

from audiotrails.podcasts.models import Category

from ..defaulttags import (
    active_link,
    button,
    format_duration,
    htmlattrs,
    jsonify,
    keepspaces,
    login_url,
    percent,
    share_buttons,
)


class TestFormatDuration:
    def test_format_duration_if_empty(self):
        assert format_duration(None) == ""
        assert format_duration(0) == ""

    def test_format_duration_if_less_than_one_minute(self):
        assert format_duration(30) == "<1min"

    def test_format_duration_if_less_than_ten_minutes(self):
        assert format_duration(540) == "9min"

    def test_format_duration_if_less_than_one_hour(self):
        assert format_duration(2400) == "40min"

    def test_format_duration_if_more_than_one_hour(self):
        assert format_duration(9000) == "2h 30min"


class TestLoginUrl:
    def test_login_url(self):
        url = "/podcasts/1234/test"
        assert login_url(url) == "/account/login/?next=/podcasts/1234/test"

    def test_login_url_with_query_string(self):
        url = "/podcasts/1234/test?ok=true"
        assert login_url(url) == "/account/login/?next=/podcasts/1234/test%3Fok%3Dtrue"


class TestHtmlAttrs:
    def test_empty_dict(self):
        assert htmlattrs(None) == ""
        assert htmlattrs("") == ""
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

    def test_value_does_not_have_body(self):
        return keepspaces("\n    ") == ""

    def test_value_has_html(self):
        return keepspaces("test<br />this<ul><li>hello</li></ul>") == "test this hello"


class TestButtonComponent:
    def test_context_is_button(self):
        ctx = button("test")
        assert ctx["tag"] == "button"

    def test_context_is_link(self):
        ctx = button("test", href="/")
        assert ctx["tag"] == "a"


class TestShareButtons:
    def test_share_buttons(self, rf):
        url = "/podcasts/1234/test/"
        context = {"request": rf.get(url)}
        share_urls = share_buttons(context, url, "Test Podcast")["share_urls"]

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
