from __future__ import annotations

import dataclasses

import pytest

from django.template.context import RequestContext
from django.template.loader import get_template
from django.urls import reverse

from radiofeed.common.template import (
    absolute_uri,
    active_link,
    format_duration,
    icon,
    markdown,
    normalize_url,
    pagination_url,
    share_buttons,
)

EXAMPLE_HTTPS_URL = "https://example.com"
EXAMPLE_HTTP_URL = "http://example.com"


@pytest.fixture
def req(rf, anonymous_user):
    req = rf.get("/")
    req.user = anonymous_user
    return req


@pytest.fixture
def auth_req(req, user):
    req.user = user
    return req


@dataclasses.dataclass
class PageObj:
    has_other_pages: bool = False
    has_next: bool = False
    has_previous: bool = False
    next_page_number: int = 0
    previous_page_number: int = 0


class TestIcon:
    def test_icon(self):
        assert icon("rss") == {
            "name": "rss",
            "style": "fa",
            "size": "",
            "title": "",
            "css_class": "",
        }

    def test_brand_icon(self):
        assert icon("facebook", style="brands") == {
            "name": "facebook",
            "style": "fa-brands",
            "size": "",
            "title": "",
            "css_class": "",
        }


class TestAbsoluteUri:
    SEARCH_URL = "/podcasts/search/"
    DETAIL_URL = "/podcasts/12345/test/"

    def test_has_request_no_url(self, db, rf):
        url = absolute_uri(RequestContext(rf.get("/")))
        assert url == EXAMPLE_HTTP_URL

    def test_has_request_no_url_https(self, db, rf, settings):
        settings.SECURE_SSL_REDIRECT = True
        url = absolute_uri(RequestContext(rf.get("/")))
        assert url == EXAMPLE_HTTPS_URL

    def test_has_request_static_url(self, db, rf):
        url = absolute_uri(RequestContext(rf.get("/")), self.SEARCH_URL)
        assert url == EXAMPLE_HTTP_URL + self.SEARCH_URL

    def test_has_request_resolved_url(self, db, rf):
        url = absolute_uri(
            RequestContext(rf.get("/")),
            "podcasts:podcast_detail",
            podcast_id=12345,
            slug="test",
        )
        assert url == EXAMPLE_HTTP_URL + self.DETAIL_URL

    def test_has_request_from_model(self, rf, podcast):
        url = absolute_uri(RequestContext(rf.get("/")), podcast)
        assert url == EXAMPLE_HTTP_URL + podcast.get_absolute_url()

    def test_not_has_request_no_url(self, db):
        url = absolute_uri(RequestContext(request=None))
        assert url == EXAMPLE_HTTP_URL

    def test_not_has_request_no_url_https(self, db, settings):
        settings.SECURE_SSL_REDIRECT = True
        url = absolute_uri(RequestContext(request=None))
        assert url == EXAMPLE_HTTPS_URL

    def test_not_has_request_static_url(self, db):
        url = absolute_uri(RequestContext(request=None), self.SEARCH_URL)
        assert url == EXAMPLE_HTTP_URL + self.SEARCH_URL

    def test_not_has_request_resolved_url(self, db):
        url = absolute_uri(
            RequestContext(request=None),
            "podcasts:podcast_detail",
            podcast_id=12345,
            slug="test",
        )
        assert url == EXAMPLE_HTTP_URL + self.DETAIL_URL

    def test_not_has_request_model(self, podcast):
        url = absolute_uri(RequestContext(request=None), podcast)
        assert url == EXAMPLE_HTTP_URL + podcast.get_absolute_url()


class TestFormatDuration:
    @pytest.mark.parametrize(
        "duration,expected",
        [
            (None, ""),
            (0, ""),
            (30, ""),
            (540, "9min"),
            (2400, "40min"),
            (9000, "2h 30min"),
        ],
    )
    def test_format_duration(self, duration, expected):
        assert format_duration(duration) == expected


class TestActiveLink:
    episodes_url = "episodes:index"

    def test_active_link_no_match(self, rf):
        url = reverse("account_login")
        req = rf.get(url)
        link = active_link(RequestContext(req), self.episodes_url)
        assert link.url == reverse(self.episodes_url)
        assert link.css == "link"
        assert not link.active

    def test_active_link_match(self, rf):
        url = reverse(self.episodes_url)
        req = rf.get(url)
        link = active_link(RequestContext(req), self.episodes_url)
        assert link.url == reverse(self.episodes_url)
        assert link.css == "link active"
        assert link.active


class TestShareButtons:
    def test_share_buttons(self, rf):
        url = "/podcasts/12344/test/"
        share_urls = share_buttons(RequestContext(rf.get(url)), url, "Test Podcast")[
            "share_urls"
        ]

        assert (
            share_urls["email"]
            == "mailto:?subject=Test%20Podcast&body=http%3A//testserver/podcasts/12344/test/"
        )

        assert (
            share_urls["facebook"]
            == "https://www.facebook.com/sharer/sharer.php?u=http%3A//testserver/podcasts/12344/test/"
        )

        assert (
            share_urls["twitter"]
            == "https://twitter.com/share?url=http%3A//testserver/podcasts/12344/test/&text=Test%20Podcast"
        )

        assert (
            share_urls["linkedin"]
            == "https://www.linkedin.com/sharing/share-offsite/?url=http%3A//testserver/podcasts/12344/test/"
        )


class TestMarkdown:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, ""),
            ("", ""),
            ("   ", ""),
            ("test", "test"),
            ("*test*", "<b>test</b>"),
            ("<p>test</p>", "<p>test</p>"),
            ("<p>test</p>   ", "<p>test</p>"),
            ("<script>test</script>", "test"),
        ],
    )
    def test_markdown(self, value, expected):
        return markdown(value) == {"content": expected}


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


class TestPaginationUrl:
    def test_append_page_number_to_querystring(self, rf):

        req = rf.get("/search/", {"query": "test"})
        url = pagination_url(RequestContext(req), 5)
        assert url.startswith("/search/?")
        assert "query=test" in url
        assert "page=5" in url


class TestNavbar:
    @pytest.fixture
    def tmpl(self):
        return get_template("includes/navbar.html")

    def test_authenticated(self, tmpl, auth_req):
        rendered = tmpl.render({}, request=auth_req)
        assert auth_req.user.username in rendered

    def test_anonymous(self, tmpl, req):
        rendered = tmpl.render({}, request=req)
        assert "About this Site" in rendered


class TestPaginationLinks:
    @pytest.fixture
    def tmpl(self):
        return get_template("includes/pagination_links.html")

    def test_no_pagination(self, req, tmpl):
        ctx = {
            "page_obj": PageObj(has_other_pages=False),
        }
        rendered = tmpl.render(ctx, request=req)
        assert "Pagination" not in rendered

    def test_has_next(self, req, tmpl):
        ctx = {
            "page_obj": PageObj(
                has_other_pages=True, has_next=True, next_page_number=2
            ),
        }
        rendered = tmpl.render(ctx, request=req)
        assert rendered.count("No More Pages") == 2

    def test_has_previous(self, req, tmpl):
        ctx = {
            "page_obj": PageObj(
                has_other_pages=True, has_previous=True, previous_page_number=1
            ),
        }
        rendered = tmpl.render(ctx, request=req)
        assert rendered.count("No More Pages") == 2

    def test_has_next_and_previous(self, req, tmpl):
        ctx = {
            "page_obj": PageObj(
                has_other_pages=True,
                has_previous=True,
                has_next=True,
                previous_page_number=1,
                next_page_number=3,
            ),
        }
        rendered = tmpl.render(ctx, request=req)
        assert rendered.count("No More Pages") == 0


class TestFormFields:
    @pytest.fixture
    def tmpl(self):
        return get_template("includes/form_field.html")

    def test_is_hidden(self, tmpl, mocker):
        field = mocker.Mock()
        field.is_hidden = True
        assert tmpl.render({"field": field}, request=req)

    def test_textinput(self, tmpl, mocker):
        field = mocker.Mock()
        field.is_hidden = False
        field.field.widget = mocker.Mock(spec="django.forms.widgets.TextInput")
        field.errors = []
        assert tmpl.render({"field": field}, request=req)

    def test_checkboxinput(self, tmpl, mocker):
        field = mocker.Mock()
        field.is_hidden = False
        field.field.widget = mocker.Mock(spec="django.forms.widgets.CheckboxInput")
        field.errors = []
        assert tmpl.render({"field": field}, request=req)

    def test_fileinput(self, tmpl, mocker):
        field = mocker.Mock()
        field.is_hidden = False
        field.field.widget = mocker.Mock(spec="django.forms.widgets.CheckboxInput")
        field.errors = []
        assert tmpl.render({"field": field}, request=req)

    def test_errors(self, tmpl, mocker):
        field = mocker.Mock()
        field.is_hidden = False
        field.field.widget = mocker.Mock(spec="django.forms.widgets.TextInput")
        field.errors = ["error"]
        assert tmpl.render({"field": field}, request=req)
