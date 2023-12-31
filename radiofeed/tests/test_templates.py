import pytest
from django.template.loader import get_template
from django_htmx.middleware import HtmxDetails


class TestErrorTemplates:
    @pytest.fixture()
    def context(self, rf):
        return {"request": rf.get("/")}

    def test_bad_request(self, context):
        assert get_template("400.html").render(context)

    def test_not_found(self, context):
        assert get_template("400.html").render(context)

    def test_forbidden(self, context):
        assert get_template("403.html").render(context)

    def test_not_allowed(self, context):
        assert get_template("405.html").render(context)

    def test_server_error(self, context):
        assert get_template("500.html").render(context)

    def test_csrf_error(self, context):
        assert get_template("403_csrf.html").render(context)


class TestFormTemplates:
    @pytest.fixture()
    def req(self, rf, anonymous_user):
        req = rf.get("/")
        req.user = anonymous_user
        return req

    @pytest.fixture()
    def tmpl(self):
        return get_template("django/forms/field.html")

    @pytest.fixture()
    def field(self, mocker):
        return mocker.Mock()

    def test_is_hidden(self, req, tmpl, field):
        field.is_hidden = True
        assert tmpl.render({"field": field}, request=req)

    def test_textinput(self, req, tmpl, mocker, field):
        field.is_hidden = False
        field.field.widget = mocker.Mock(spec="django.forms.widgets.TextInput")
        field.errors = []
        assert tmpl.render({"field": field}, request=req)

    def test_checkboxinput(self, req, tmpl, mocker, field):
        field.is_hidden = False
        field.field.widget = mocker.Mock(spec="django.forms.widgets.CheckboxInput")
        field.errors = []
        assert tmpl.render({"field": field}, request=req)

    def test_fileinput(self, req, tmpl, mocker, field):
        field.is_hidden = False
        field.field.widget = mocker.Mock(spec="django.forms.widgets.CheckboxInput")
        field.errors = []
        assert tmpl.render({"field": field}, request=req)

    def test_errors(self, req, tmpl, mocker, field):
        field.is_hidden = False
        field.field.widget = mocker.Mock(spec="django.forms.widgets.TextInput")
        field.errors = ["error"]
        assert tmpl.render({"field": field}, request=req)


class TestBaseTemplates:
    @pytest.fixture()
    def tmpl(self):
        return get_template("about.html")

    @pytest.fixture()
    def player(self, mocker):
        player = mocker.Mock()
        player.get.return_value = None
        return player

    def test_default(self, rf, anonymous_user, player):
        req = rf.get("/")
        req.user = anonymous_user
        req.player = player
        tmpl = get_template("about.html")
        assert tmpl.render({}, request=req)

    def test_htmx(self, rf, anonymous_user, player):
        req = rf.get("/", HTTP_HX_REQUEST="true")
        req.htmx = HtmxDetails(req)
        req.user = anonymous_user
        req.player = player
        tmpl = get_template("about.html")
        assert tmpl.render(
            {
                "messages": [
                    {
                        "message": "test",
                        "tags": "success",
                    },
                ],
            },
            request=req,
        )
