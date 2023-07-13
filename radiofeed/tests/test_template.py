import pytest
from django.template.context import RequestContext
from django.template.loader import get_template
from django.urls import reverse, reverse_lazy
from django_htmx.middleware import HtmxDetails

from radiofeed.template import active_link, cover_image, format_duration, markdown


@pytest.fixture()
def req(rf, anonymous_user):
    req = rf.get("/")
    req.user = anonymous_user
    return req


@pytest.fixture()
def auth_req(req, user):
    req.user = user
    return req


class TestFormatDuration:
    @pytest.mark.parametrize(
        ("duration", "expected"),
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


class TestCoverImage:
    def test_is_cover_url(self):
        assert cover_image("https://example.com/test.jpg", 100, "test img")["cover_url"]

    def test_is_not_cover_url(self):
        assert cover_image("", 100, "test img")["cover_url"] == ""


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
        ("value", "expected"),
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


class TestNavbar:
    @pytest.fixture()
    def tmpl(self):
        return get_template("_navbar.html")

    @pytest.mark.django_db()
    def test_authenticated(self, tmpl, auth_req):
        rendered = tmpl.render({}, request=auth_req)
        assert auth_req.user.username in rendered

    def test_anonymous(self, tmpl, req):
        rendered = tmpl.render({}, request=req)
        assert "About this Site" in rendered


class MockForm:
    fields = []
    non_field_errors = []

    def __iter__(self):
        return iter(self.fields)


class TestDefaultForm:
    @pytest.fixture()
    def tmpl(self):
        return get_template("django/forms/default.html")

    @pytest.fixture()
    def form(self):
        return MockForm()

    @pytest.fixture()
    def field(self, mocker):
        return mocker.Mock()

    def test_is_hidden(self, tmpl, form, field):
        field.is_hidden = True
        form.fields = [field]
        assert tmpl.render({"form": form}, request=req)

    def test_textinput(self, tmpl, mocker, form, field):
        field.is_hidden = False
        field.field.widget = mocker.Mock(spec="django.forms.widgets.TextInput")
        field.errors = []
        form.fields = [field]
        assert tmpl.render({"form": form}, request=req)

    def test_checkboxinput(self, tmpl, mocker, form, field):
        field.is_hidden = False
        field.field.widget = mocker.Mock(spec="django.forms.widgets.CheckboxInput")
        field.errors = []
        form.fields = [field]
        assert tmpl.render({"form": form}, request=req)

    def test_fileinput(self, tmpl, mocker, form, field):
        field.is_hidden = False
        field.field.widget = mocker.Mock(spec="django.forms.widgets.CheckboxInput")
        field.errors = []
        form.fields = [field]
        assert tmpl.render({"form": form}, request=req)

    def test_errors(self, tmpl, mocker, form, field):
        field.is_hidden = False
        field.field.widget = mocker.Mock(spec="django.forms.widgets.TextInput")
        field.errors = ["error"]
        form.fields = [field]
        assert tmpl.render({"form": form}, request=req)

    def test_non_field_errors(self, tmpl, form):
        form.non_field_errors = ["error!"]
        assert tmpl.render({"form": form}, request=req)


class TestBaseTemplates:
    @pytest.fixture()
    def tmpl(self):
        return get_template("about.html")

    def test_default(self, rf):
        req = rf.get("/")
        tmpl = get_template("about.html")
        assert tmpl.render({}, request=req)

    def test_htmx(self, rf):
        req = rf.get("/", HTTP_HX_REQUEST="true")
        req.htmx = HtmxDetails(req)
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
