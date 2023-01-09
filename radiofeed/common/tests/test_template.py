from __future__ import annotations

import dataclasses

import pytest

from django.template.context import RequestContext
from django.template.loader import get_template
from django.urls import reverse

from radiofeed.common.template import (
    absolute_uri,
    active_link,
    cover_image,
    force_url,
    format_duration,
    icon,
    markdown,
    pagination_url,
)


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
    BASE_URL = "http://example.com"

    SEARCH_URL = "/podcasts/search/"
    DETAIL_URL = "/podcasts/12345/test/"

    def test_no_url(self, db):
        assert absolute_uri({}) == self.BASE_URL + "/"

    def test_request(self, rf):
        assert absolute_uri({"request": rf.get("/")}) == "http://testserver/"

    def test_https(self, db, settings):
        settings.SECURE_SSL_REDIRECT = True
        assert absolute_uri({}) == "https://example.com/"

    def test_static_url(self, db):
        url = absolute_uri({}, self.SEARCH_URL)
        assert url == self.BASE_URL + self.SEARCH_URL

    def test_resolved_url(self, db):
        url = absolute_uri({}, "podcasts:podcast_detail", podcast_id=12345, slug="test")
        assert url == self.BASE_URL + self.DETAIL_URL

    def test_model(self, podcast, db):
        url = absolute_uri({}, podcast)
        assert url == self.BASE_URL + podcast.get_absolute_url()


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


class TestForceUrl:
    base_url = "www.newstatesman.com/podcast"
    expected_url = "https://" + base_url

    def test_none(self):
        assert force_url(None) == ""

    def test_empty(self):
        assert force_url("") == ""

    def test_missing_http(self):
        assert force_url(self.base_url) == self.expected_url

    def test_already_complete(self):
        assert force_url(self.expected_url) == self.expected_url


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
        return get_template("includes/forms/field.html")

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


class TestCoverImage:
    def test_is_cover_url(self):
        assert cover_image("https://example.com/test.jpg", 100, "test img")["cover_url"]

    def test_is_not_cover_url(self):
        assert (
            cover_image("", 100, "test img")["cover_url"]
            == "/static/img/placeholder-100.webp"
        )
