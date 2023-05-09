import dataclasses

import pytest
from django.template.context import RequestContext
from django.template.loader import get_template
from django.urls import reverse, reverse_lazy

from radiofeed.middleware import Pagination
from radiofeed.template import (
    active_link,
    cover_image,
    force_url,
    format_duration,
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
    episodes_url = reverse_lazy("episodes:index")

    def test_active_link_no_match(self, rf):
        url = reverse("account_login")
        req = rf.get(url)

        assert active_link(RequestContext(req), self.episodes_url) == {
            "url": self.episodes_url,
            "css": "link",
            "active": False,
        }

    def test_active_link_match(self, rf):
        req = rf.get(self.episodes_url)

        assert active_link(RequestContext(req), self.episodes_url) == {
            "url": self.episodes_url,
            "css": "link active",
            "active": True,
        }


class TestMarkdown:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, ""),
            ("", ""),
            ("   ", ""),
            ("test", "test"),
            ("<p>test</p>", "<p>test</p>"),
            ("<p>test</p>   ", "<p>test</p>"),
            ("<script>test</script>", "test"),
        ],
    )
    def test_markdown(self, value, expected):
        return markdown(value) == {"content": expected}


class TestForceUrl:
    base_url = "www.newstatesman.com/podcast"
    full_url = "https://" + base_url

    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, ""),
            ("", ""),
            ("random-string", ""),
            (base_url, full_url),
            (full_url, full_url),
        ],
    )
    def test_force_url(self, value, expected):
        assert force_url(value) == expected


class TestPaginationUrl:
    def test_append_page_number_to_querystring(self, rf):
        req = rf.get("/search/", {"query": "test"})
        req.pagination = Pagination(req)
        url = pagination_url(RequestContext(req), 5)
        assert url.startswith("/search/?")
        assert "query=test" in url
        assert "page=5" in url


class TestNavbar:
    @pytest.fixture
    def tmpl(self):
        return get_template("_navbar.html")

    @pytest.mark.django_db
    def test_authenticated(self, tmpl, auth_req):
        rendered = tmpl.render({}, request=auth_req)
        assert auth_req.user.username in rendered

    def test_anonymous(self, tmpl, req):
        rendered = tmpl.render({}, request=req)
        assert "About this Site" in rendered


class TestPaginationLinks:
    @pytest.fixture
    def tmpl(self):
        return get_template("_pagination_links.html")

    @pytest.fixture
    def page_req(self, req):
        req.pagination = Pagination(req)
        return req

    def test_no_pagination(self, page_req, tmpl):
        ctx = {
            "page_obj": PageObj(has_other_pages=False),
        }
        rendered = tmpl.render(ctx, request=page_req)
        assert "Pagination" not in rendered

    def test_has_next(self, page_req, tmpl):
        ctx = {
            "page_obj": PageObj(
                has_other_pages=True, has_next=True, next_page_number=2
            ),
        }
        rendered = tmpl.render(ctx, request=page_req)
        assert rendered.count("No More Pages") == 2

    def test_has_previous(self, page_req, tmpl):
        ctx = {
            "page_obj": PageObj(
                has_other_pages=True, has_previous=True, previous_page_number=1
            ),
        }
        rendered = tmpl.render(ctx, request=page_req)
        assert rendered.count("No More Pages") == 2

    def test_has_next_and_previous(self, page_req, tmpl):
        ctx = {
            "page_obj": PageObj(
                has_other_pages=True,
                has_previous=True,
                has_next=True,
                previous_page_number=1,
                next_page_number=3,
            ),
        }
        rendered = tmpl.render(ctx, request=page_req)
        assert rendered.count("No More Pages") == 0


class MockForm:
    fields = []
    non_field_errors = []

    def __iter__(self):
        return iter(self.fields)


class TestDefaultForm:
    @pytest.fixture
    def tmpl(self):
        return get_template("django/forms/default.html")

    @pytest.fixture
    def form(self):
        return MockForm()

    def test_is_hidden(self, tmpl, mocker, form):
        field = mocker.Mock()
        field.is_hidden = True
        form.fields = [field]
        assert tmpl.render({"form": form}, request=req)

    def test_textinput(self, tmpl, mocker, form):
        field = mocker.Mock()
        field.is_hidden = False
        field.field.widget = mocker.Mock(spec="django.forms.widgets.TextInput")
        field.errors = []
        form.fields = [field]
        assert tmpl.render({"form": form}, request=req)

    def test_checkboxinput(self, tmpl, mocker, form):
        field = mocker.Mock()
        field.is_hidden = False
        field.field.widget = mocker.Mock(spec="django.forms.widgets.CheckboxInput")
        field.errors = []
        form.fields = [field]
        assert tmpl.render({"form": form}, request=req)

    def test_fileinput(self, tmpl, mocker, form):
        field = mocker.Mock()
        field.is_hidden = False
        field.field.widget = mocker.Mock(spec="django.forms.widgets.CheckboxInput")
        field.errors = []
        form.fields = [field]
        assert tmpl.render({"form": form}, request=req)

    def test_errors(self, tmpl, mocker, form):
        field = mocker.Mock()
        field.is_hidden = False
        field.field.widget = mocker.Mock(spec="django.forms.widgets.TextInput")
        field.errors = ["error"]
        form.fields = [field]
        assert tmpl.render({"form": form}, request=req)

    def test_non_field_errors(self, tmpl, mocker, form):
        form.non_field_errors = ["error!"]
        assert tmpl.render({"form": form}, request=req)


class TestCoverImage:
    def test_is_cover_url(self):
        assert cover_image("https://example.com/test.jpg", 100, "test img")["cover_url"]

    def test_is_not_cover_url(self):
        assert cover_image("", 100, "test img")["cover_url"] == ""
