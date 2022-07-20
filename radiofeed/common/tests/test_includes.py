from __future__ import annotations

import dataclasses

import pytest

from django.template.loader import get_template


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
        return get_template("forms/field.html")

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
