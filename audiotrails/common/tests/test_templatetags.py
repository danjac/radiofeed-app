from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from audiotrails.common.pagination.templatetags import pagination_url
from audiotrails.common.template.defaulttags import (
    active_link,
    format_duration,
    get_privacy_details,
    keepspaces,
    login_url,
    percent,
    re_active_link,
    share_buttons,
)
from audiotrails.podcasts.models import Category


class FormatDurationTests(SimpleTestCase):
    def test_format_duration_if_empty(self) -> None:
        self.assertEqual(format_duration(None), "")
        self.assertEqual(format_duration(0), "")

    def test_format_duration_if_less_than_one_minute(self) -> None:
        self.assertEqual(format_duration(30), "<1min")

    def test_format_duration_if_less_than_ten_minutes(self) -> None:
        self.assertEqual(format_duration(540), "9min")

    def test_format_duration_if_less_than_one_hour(self) -> None:
        self.assertEqual(format_duration(2400), "40min")

    def test_format_duration_if_more_than_one_hour(self) -> None:
        self.assertEqual(format_duration(9000), "2h 30min")


class LoginUrlTests(SimpleTestCase):
    def test_login_url(self) -> None:
        url = "/podcasts/1234/test"
        self.assertEqual(login_url(url), "/account/login/?next=/podcasts/1234/test")

    def test_login_url_with_query_string(self) -> None:
        url = "/podcasts/1234/test?ok=true"
        self.assertEqual(
            login_url(url), "/account/login/?next=/podcasts/1234/test%3Fok%3Dtrue"
        )


class PercentTests(SimpleTestCase):
    def test_if_either_none(self) -> None:
        self.assertEqual(percent(10, 0), 0)
        self.assertEqual(percent(0, 10), 0)
        self.assertEqual(percent(0, 0), 0)
        self.assertEqual(percent(None, None), 0)

    def test_percent(self) -> None:
        self.assertEqual(percent(30, 60), 50)


class ActiveLinkTests(SimpleTestCase):
    podcasts_url = "podcasts:index"
    categories_url = "podcasts:categories"

    def setUp(self) -> None:
        self.rf = RequestFactory()

    def test_active_link_no_match(self) -> None:
        url = reverse("account_login")
        req = self.rf.get(url)
        route = active_link({"request": req}, self.podcasts_url)
        self.assertEqual(route.url, reverse(self.podcasts_url))
        self.assertFalse(route.match)
        self.assertFalse(route.exact)

    def test_active_link_non_exact_match(self) -> None:
        url = Category(id=1234, name="test").get_absolute_url()
        req = self.rf.get(url)
        route = active_link({"request": req}, self.categories_url)
        self.assertEqual(route.url, reverse(self.categories_url))
        self.assertTrue(route.match)
        self.assertFalse(route.exact)

    def test_active_link_exact_match(self) -> None:
        url = reverse(self.podcasts_url)
        req = self.rf.get(url)
        route = active_link({"request": req}, self.podcasts_url)
        self.assertEqual(route.url, reverse(self.podcasts_url))
        self.assertTrue(route.match)
        self.assertTrue(route.exact)


class ReActiveLinkTests(SimpleTestCase):
    categories_url = "podcasts:categories"

    def setUp(self) -> None:
        self.rf = RequestFactory()

    def test_re_active_link_no_match(self) -> None:
        url = reverse("account_login")
        req = self.rf.get(url)
        route = re_active_link({"request": req}, self.categories_url, "/discover/*")
        self.assertEqual(route.url, reverse(self.categories_url))
        self.assertFalse(route.match)
        self.assertFalse(route.exact)

    def test_active_link_non_exact_match(self) -> None:
        url = Category(id=1234, name="test").get_absolute_url()
        req = self.rf.get(url)
        route = re_active_link({"request": req}, self.categories_url, "/discover/*")
        self.assertEqual(route.url, reverse(self.categories_url))
        self.assertTrue(route.match)
        self.assertFalse(route.exact)


class KeepspacesTests(SimpleTestCase):
    def test_value_is_empty(self) -> None:
        self.assertEqual(keepspaces(""), "")

    def test_value_is_none(self) -> None:
        self.assertEqual(keepspaces(None), "")

    def test_value_does_not_have_body(self) -> None:
        self.assertEqual(keepspaces("\n    "), "")

    def test_value_has_html(self) -> None:
        self.assertEqual(
            keepspaces("test<br />this<ul><li>hello</li></ul>"), "test this hello"
        )

    def test_value_has_no_body(self) -> None:
        self.assertEqual(keepspaces("<div>"), "")


class PrivacyDetailsTests(SimpleTestCase):
    def test_get_privacy_details(self) -> None:
        self.assertTrue(get_privacy_details())


class ShareButtonsTests(SimpleTestCase):
    def test_share_buttons(self) -> None:
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
    def test_append_page_number_to_querystring(self) -> None:

        req = RequestFactory().get("/search/", {"q": "test"})
        url = pagination_url({"request": req}, 5)
        self.assertTrue(url.startswith("/search/?"))
        self.assertIn("q=test", url)
        self.assertIn("page=5", url)
