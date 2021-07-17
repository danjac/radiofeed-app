from django.urls import reverse

from jcasts.podcasts.models import Category
from jcasts.shared.pagination.templatetags import pagination_url
from jcasts.shared.template.defaulttags import (
    active_link,
    format_duration,
    get_privacy_details,
    keepspaces,
    login_url,
    re_active_link,
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


class TestActiveLink:
    podcasts_url = "podcasts:index"
    categories_url = "podcasts:categories"

    def test_active_link_no_match(self, rf):
        url = reverse("account_login")
        req = rf.get(url)
        route = active_link({"request": req}, self.podcasts_url)
        assert route.url == reverse(self.podcasts_url)
        assert not route.match
        assert not route.exact

    def test_active_link_non_exact_match(self, rf):
        url = Category(id=1234, name="test").get_absolute_url()
        req = rf.get(url)
        route = active_link({"request": req}, self.categories_url)
        assert route.url == reverse(self.categories_url)
        assert route.match
        assert not route.exact

    def test_active_link_exact_match(self, rf):
        url = reverse(self.podcasts_url)
        req = rf.get(url)
        route = active_link({"request": req}, self.podcasts_url)
        assert route.url == reverse(self.podcasts_url)
        assert route.match
        assert route.exact


class TestReActiveLink:
    categories_url = "podcasts:categories"

    def test_re_active_link_no_match(self, rf):
        url = reverse("account_login")
        req = rf.get(url)
        route = re_active_link({"request": req}, self.categories_url, "/discover/*")
        assert route.url == reverse(self.categories_url)
        assert not route.match
        assert not route.exact

    def test_active_link_non_exact_match(self, rf):
        url = Category(id=1234, name="test").get_absolute_url()
        req = rf.get(url)
        route = re_active_link({"request": req}, self.categories_url, "/discover/*")
        assert route.url == reverse(self.categories_url)
        assert route.match
        assert not route.exact


class TestKeepspaces:
    def test_value_is_empty(self):
        assert keepspaces("") == ""

    def test_value_is_none(self):
        assert keepspaces(None) == ""

    def test_value_does_not_have_body(self):
        assert keepspaces("\n    ") == ""

    def test_value_has_html(self):
        assert keepspaces("test<br />this<ul><li>hello</li></ul>") == "test this hello"

    def test_value_has_no_html_content(self):
        assert keepspaces("test") == "test"


class TestPrivacyDetails:
    def test_get_privacy_details(self):
        assert get_privacy_details()


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


class TestPaginationUrl:
    def test_append_page_number_to_querystring(self, rf):

        req = rf.get("/search/", {"q": "test"})
        url = pagination_url({"request": req}, 5)
        assert url.startswith("/search/?")
        assert "q=test" in url
        assert "page=5" in url
