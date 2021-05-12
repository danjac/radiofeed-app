from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from audiotrails.podcasts.models import Category

from ..pagination.templatetags import pagination_url
from ..template.defaulttags import (
    active_link,
    format_duration,
    htmlattrs,
    jsonify,
    keepspaces,
    login_url,
    percent,
    share_buttons,
)


class FormatDurationTests(SimpleTestCase):
    def test_format_duration_if_empty(self):
        self.assertEqual(format_duration(None), "")
        self.assertEqual(format_duration(0), "")

    def test_format_duration_if_less_than_one_minute(self):
        self.assertEqual(format_duration(30), "<1min")

    def test_format_duration_if_less_than_ten_minutes(self):
        self.assertEqual(format_duration(540), "9min")

    def test_format_duration_if_less_than_one_hour(self):
        self.assertEqual(format_duration(2400), "40min")

    def test_format_duration_if_more_than_one_hour(self):
        self.assertEqual(format_duration(9000), "2h 30min")


class LoginUrlTests(SimpleTestCase):
    def test_login_url(self):
        url = "/podcasts/1234/test"
        self.assertEqual(login_url(url), "/account/login/?next=/podcasts/1234/test")

    def test_login_url_with_query_string(self):
        url = "/podcasts/1234/test?ok=true"
        self.assertEqual(
            login_url(url), "/account/login/?next=/podcasts/1234/test%3Fok%3Dtrue"
        )


class HtmlAttrsTests(SimpleTestCase):
    def test_empty_dict(self):
        self.assertEqual(htmlattrs(None), "")
        self.assertEqual(htmlattrs(""), "")
        self.assertEqual(htmlattrs({}), "")

    def test_attrs(self):
        self.assertEqual(
            htmlattrs({"data_action": "submit", "type": "button"}),
            'data-action="submit" type="button"',
        )


class JsonifyTests(SimpleTestCase):
    def test_jsonify(self):
        self.assertEqual(jsonify({"title": "test"}), '{"title": "test"}')


class PercentTests(SimpleTestCase):
    def test_if_either_none(self):
        self.assertEqual(percent(10, 0), 0)
        self.assertEqual(percent(0, 10), 0)
        self.assertEqual(percent(0, 0), 0)
        self.assertEqual(percent(None, None), 0)

    def test_percent(self):
        self.assertEqual(percent(30, 60), 50)


class ActiveLinkTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_active_link_no_match(self):
        url = reverse("account_login")
        req = self.rf.get(url)
        route = active_link({"request": req}, "podcasts:index")
        self.assertEqual(route.url, reverse("podcasts:index"))
        self.assertFalse(route.match)
        self.assertFalse(route.exact)

    def test_active_link_non_exact_match(self):
        url = Category(id=1234, name="test").get_absolute_url()
        req = self.rf.get(url)
        route = active_link({"request": req}, "podcasts:categories")
        self.assertEqual(route.url, reverse("podcasts:categories"))
        self.assertTrue(route.match)
        self.assertFalse(route.exact)

    def test_active_link_exact_match(self):
        url = reverse("podcasts:index")
        req = self.rf.get(url)
        route = active_link({"request": req}, "podcasts:index")
        self.assertEqual(route.url, reverse("podcasts:index"))
        self.assertTrue(route.match)
        self.assertTrue(route.exact)


class KeepspacesTests(SimpleTestCase):
    def test_value_is_none(self):
        self.assertEqual(keepspaces(None), "")

    def test_value_does_not_have_body(self):
        self.assertEqual(keepspaces("\n    "), "")

    def test_value_has_html(self):
        self.assertEqual(
            keepspaces("test<br />this<ul><li>hello</li></ul>"), "test this hello"
        )


class ShareButtonsTests(SimpleTestCase):
    def test_share_buttons(self):
        url = "/podcasts/1234/test/"
        context = {"request": RequestFactory().get(url)}
        share_urls = share_buttons(context, url, "Test Podcast")["share_urls"]

        self.assertEqual(
            share_urls["email"],
            "mailto:?subject=Test%20Podcast&body=http%3A//testserver/podcasts/1234/test/",
        )

        self.assertEqual(
            share_urls["facebook"],
            "https://www.facebook.com/sharer/sharer.php?u=http%3A//testserver/podcasts/1234/test/",
        )

        self.assertEqual(
            share_urls["twitter"],
            "https://twitter.com/share?url=http%3A//testserver/podcasts/1234/test/&text=Test%20Podcast",
        )

        self.assertEqual(
            share_urls["linkedin"],
            "https://www.linkedin.com/sharing/share-offsite/?url=http%3A//testserver/podcasts/1234/test/",
        )


class PaginationUrlTests(SimpleTestCase):
    def test_append_page_number_to_querystring(self):

        req = RequestFactory().get("/search/", {"q": "test"})
        url = pagination_url({"request": req}, 5)
        self.assertTrue(url.startswith("/search/?"))
        self.assertIn("q=test", url)
        self.assertIn("page=5", url)
