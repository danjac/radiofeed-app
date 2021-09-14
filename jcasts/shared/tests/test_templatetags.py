from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from jcasts.shared.pagination.templatetags import pagination_url
from jcasts.shared.template.defaulttags import (
    absolute_uri,
    active_link,
    colorpicker,
    format_duration,
    login_url,
    markup,
    normalize_url,
    re_active_link,
    safe_url,
    share_buttons,
    signup_url,
    timesince_approx,
)


class TestTimesinceApprox:
    def test_none(self):
        assert timesince_approx(None) == ""

    def test_value(self):
        assert (
            timesince_approx(timezone.now() - timedelta(days=3, hours=5)) == "3\xa0days"
        )


class TestColorpicker:
    colors = "red,blue,green,purple"

    def test_empty(self):
        assert colorpicker("", self.colors) == "red"

    def test_not_empty(self):
        assert colorpicker("aaaa", self.colors) == "blue"
        assert colorpicker("bbbb", self.colors) == "green"
        assert colorpicker("cccc", self.colors) == "purple"
        assert colorpicker("dddd", self.colors) == "red"


class TestAbsoluteUri:
    def test_has_request_no_url(self, rf):
        url = absolute_uri({"request": rf.get("/")})
        assert url == "http://testserver/"

    def test_has_request_no_url_https(self, rf, settings):
        settings.SECURE_SSL_REDIRECT = True
        url = absolute_uri({"request": rf.get("/")})
        assert url == "http://testserver/"

    def test_has_request_static_url(self, rf):
        url = absolute_uri({"request": rf.get("/")}, "/podcasts/search/")
        assert url == "http://testserver/podcasts/search/"

    def test_has_request_resolved_url(self, rf):
        url = absolute_uri(
            {"request": rf.get("/")},
            "podcasts:podcast_detail",
            podcast_id=12345,
            slug="test",
        )
        assert url == "http://testserver/podcasts/12345/test/"

    def test_has_request_from_model(self, rf, podcast):
        url = absolute_uri(
            {"request": rf.get("/")},
            podcast,
        )
        assert url == "http://testserver" + podcast.get_absolute_url()

    def test_not_has_request_no_url(self, db):
        url = absolute_uri({})
        assert url == "http://example.com"

    def test_not_has_request_no_url_https(self, db, settings):
        settings.SECURE_SSL_REDIRECT = True
        url = absolute_uri({})
        assert url == "https://example.com"

    def test_not_has_request_static_url(self, db):
        url = absolute_uri({}, "/podcasts/search/")
        assert url == "http://example.com/podcasts/search/"

    def test_not_has_request_resolved_url(self, db):
        url = absolute_uri(
            {},
            "podcasts:podcast_detail",
            podcast_id=12345,
            slug="test",
        )
        assert url == "http://example.com/podcasts/12345/test/"

    def test_not_has_request_model(self, podcast):
        url = absolute_uri({}, podcast)
        assert url == "http://example.com" + podcast.get_absolute_url()


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
        url = "/podcasts/1234/test/"
        assert login_url(url) == "/account/login/?next=/podcasts/1234/test/"

    def test_login_url_with_query_string(self):
        url = "/podcasts/1234/test/?ok=true"
        assert login_url(url) == "/account/login/?next=/podcasts/1234/test/%3Fok%3Dtrue"

    def test_login_url_to_same_path(self):
        url = "/account/login/"
        assert login_url(url) == url


class TestSignupUrl:
    def test_signup_url(self):
        url = "/podcasts/1234/test/"
        assert signup_url(url) == "/account/signup/?next=/podcasts/1234/test/"

    def test_signup_url_with_query_string(self):
        url = "/podcasts/1234/test/?ok=true"
        assert (
            signup_url(url) == "/account/signup/?next=/podcasts/1234/test/%3Fok%3Dtrue"
        )

    def test_signup_url_to_same_path(self):
        url = "/account/signup/"
        assert signup_url(url) == url


class TestActiveLink:
    episodes_url = "episodes:index"

    def test_active_link_no_match(self, rf):
        url = reverse("account_login")
        req = rf.get(url)
        route = active_link({"request": req}, self.episodes_url)
        assert route.url == reverse(self.episodes_url)
        assert not route.match
        assert not route.exact

    def test_active_link_exact_match(self, rf):
        url = reverse(self.episodes_url)
        req = rf.get(url)
        route = active_link({"request": req}, self.episodes_url)
        assert route.url == reverse(self.episodes_url)
        assert route.match
        assert route.exact


class TestReActiveLink:
    about_url = "about:terms"

    def test_re_active_link_no_match(self, rf):
        url = reverse("account_login")
        req = rf.get(url)
        route = re_active_link({"request": req}, self.about_url, "/about/*")
        assert route.url == reverse(self.about_url)
        assert not route.match
        assert not route.exact

    def test_active_link_non_exact_match(self, rf):
        req = rf.get(reverse(self.about_url))
        route = re_active_link({"request": req}, self.about_url, "/about/*")
        assert route.url == reverse(self.about_url)
        assert route.match
        assert not route.exact


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


class TestMarkup:
    def test_value_none(self):
        return markup(None) == ""

    def test_value_empty(self):
        return markup("  ") == ""

    def test_markdown(self):
        return markup("*test*") == "<b>test</b>"

    def test_html(self):
        return markup("<p>test</p>") == "<p>test</p>"


class TestNormalizeUrl:
    base_url = "www.newstatesman.com/podcast"
    expected_url = "https://" + base_url

    def test_none(self):
        assert normalize_url(None) == ""

    def test_empty(self):
        assert normalize_url("") == ""

    def test_missing_http(self):
        assert normalize_url(self.base_url) == self.expected_url

    def test_already_complete(self):
        assert normalize_url(self.expected_url) == self.expected_url


class TestSafeUrl:
    def test_none(self):
        assert safe_url(None) is None

    def test_https(self):
        assert safe_url("https://example.com") == "https://example.com"

    def test_http(self):
        assert safe_url("http://example.com") == "https://example.com"

    def test_ftp(self):
        assert safe_url("ftp://example.com") is None


class TestPaginationUrl:
    def test_append_page_number_to_querystring(self, rf):

        req = rf.get("/search/", {"q": "test"})
        url = pagination_url({"request": req}, 5)
        assert url.startswith("/search/?")
        assert "q=test" in url
        assert "page=5" in url
