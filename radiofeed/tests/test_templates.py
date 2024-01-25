import pytest
from django.conf import settings
from django.template.loader import get_template
from django_htmx.middleware import HtmxDetails


class TestErrorTemplates:
    @pytest.fixture()
    def context(self, rf):
        return {"request": rf.get("/")}

    @pytest.mark.django_db()
    def test_bad_request(self, context):
        assert get_template("400.html").render(context)

    @pytest.mark.django_db()
    def test_not_found(self, context):
        assert get_template("400.html").render(context)

    @pytest.mark.django_db()
    def test_forbidden(self, context):
        assert get_template("403.html").render(context)

    @pytest.mark.django_db()
    def test_not_allowed(self, context):
        assert get_template("405.html").render(context)

    @pytest.mark.django_db()
    def test_server_error(self, context):
        assert get_template("500.html").render(context)

    @pytest.mark.django_db()
    def test_csrf_error(self, context):
        assert get_template("403_csrf.html").render(context)


class TestFormTemplates:
    @pytest.fixture()
    def req(self, rf, anonymous_user):
        req = rf.get("/")
        req.user = anonymous_user
        req.htmx = False
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
    def tmpl_context(self):
        return {"contact_email": settings.CONTACT_EMAIL}

    @pytest.fixture()
    def player(self, mocker):
        player = mocker.Mock()
        player.get.return_value = None
        return player

    @pytest.mark.django_db()
    def test_default(self, rf, anonymous_user, player, site, tmpl, tmpl_context):
        req = rf.get("/")
        req.user = anonymous_user
        req.player = player
        req.site = site
        req.htmx = False
        assert tmpl.render(tmpl_context, request=req)

    @pytest.mark.django_db()
    def test_htmx(self, rf, anonymous_user, player, site, tmpl, tmpl_context):
        req = rf.get("/", HTTP_HX_REQUEST="true")
        req.htmx = HtmxDetails(req)
        req.user = anonymous_user
        req.player = player
        req.site = site
        assert tmpl.render(
            {
                "messages": [
                    {
                        "message": "test",
                        "tags": "success",
                    },
                ],
                **tmpl_context,
            },
            request=req,
        )


class TestNavbar:
    @pytest.fixture()
    def req(self, rf, anonymous_user, site):
        req = rf.get("/")
        req.user = anonymous_user
        req.htmx = False
        req.site = site
        return req

    @pytest.fixture()
    def auth_req(self, rf, user, site):
        req = rf.get("/")
        req.user = user
        req.htmx = False
        req.site = site
        return req

    @pytest.fixture()
    def tmpl(self):
        return get_template("_navbar.html")

    @pytest.mark.django_db()
    def test_authenticated(self, tmpl, auth_req):
        rendered = tmpl.render({}, request=auth_req)
        assert auth_req.user.username in rendered

    @pytest.mark.django_db()
    def test_anonymous(self, tmpl, req):
        rendered = tmpl.render({}, request=req)
        assert "About this Site" in rendered
