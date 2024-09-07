import pytest
from django.contrib.sites.models import Site
from django.core.paginator import Paginator
from django.template import RequestContext, Template, TemplateSyntaxError
from django.urls import reverse, reverse_lazy

from radiofeed.templatetags import (
    absolute_uri,
    active_link,
    cover_art,
    format_duration,
    hx_headers,
    hx_vals,
    json_attr,
    percentage,
)


@pytest.fixture
def req(rf, anonymous_user):
    req = rf.get("/")
    req.user = anonymous_user
    req.htmx = False
    req.site = Site.objects.get_current()
    return req


@pytest.fixture
def auth_req(req, user):
    req.user = user
    return req


class TestCoverArt:
    def test_cover_art(self):
        context = cover_art(
            "https://www.example.com/test.jpg",
            "detail",
            "test image",
            css_class="hover:grayscale",
        )
        assert context["css_class"] == "size-36 lg:size-40 hover:grayscale"
        assert context["attrs"]["alt"] == "test image"
        assert context["attrs"]["title"] == "test image"


class TestPercentage:
    @pytest.mark.parametrize(
        ("value", "total", "expected"),
        [
            pytest.param(0, 0, 0, id="all zero"),
            pytest.param(50, 0, 0, id="total zero"),
            pytest.param(0, 50, 0, id="value zero"),
            pytest.param(50, 100, 50, id="50%"),
            pytest.param(150, 100, 100, id="150%"),
            pytest.param(100, 100, 100, id="100%"),
        ],
    )
    def test_percentage(self, value, total, expected):
        assert percentage(value, total) == expected


class TestFormatDuration:
    @pytest.mark.parametrize(
        ("duration", "expected"),
        [
            pytest.param(None, "", id="none"),
            pytest.param(0, "", id="zero"),
            pytest.param(30, "", id="30 seconds"),
            pytest.param(60, "1 minute", id="1 minute"),
            pytest.param(540, "9 minutes", id="9 minutes"),
            pytest.param(2400, "40 minutes", id="40 minutes"),
            pytest.param(9000, "2 hours 30 minutes", id="2 hours 30 minutes"),
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


class TestJsonAttr:
    def test_headers(self):
        assert (
            json_attr(
                "hx-headers",
                "X-CSRFToken",
                "abc123",
                "myHeader",
                "def456",
            )
            == "hx-headers='{&quot;X-CSRFToken&quot;: &quot;abc123&quot;, &quot;myHeader&quot;: &quot;def456&quot;}'"
        )

    def test_hx_headers(self):
        assert (
            hx_headers(
                "X-CSRFToken",
                "abc123",
                "myHeader",
                "def456",
            )
            == "hx-headers='{&quot;X-CSRFToken&quot;: &quot;abc123&quot;, &quot;myHeader&quot;: &quot;def456&quot;}'"
        )

    def test_hx_vals(self):
        assert (
            hx_vals("action", "cancel")
            == "hx-vals='{&quot;action&quot;: &quot;cancel&quot;}'"
        )


class TestAbsoluteUri:
    @pytest.mark.django_db
    def test_plain_url(self):
        assert absolute_uri("/podcasts/") == "http://example.com/podcasts/"

    @pytest.mark.django_db
    def test_https(self, settings):
        settings.SECURE_SSL_REDIRECT = True
        assert absolute_uri("/podcasts/") == "https://example.com/podcasts/"

    @pytest.mark.django_db
    def test_object(self, podcast):
        assert (
            absolute_uri(podcast) == f"http://example.com{podcast.get_absolute_url()}"
        )


class TestPagination:
    def test_render_tag(self, rf):
        template = Template(
            """{% pagination page_obj %}
            <span>{{ item }}</span>
        {% endpagination %}"""
        )
        items = "test string" * 20
        page_obj = Paginator(items, 12).get_page(1)

        context = RequestContext(rf.get("/"), {"page_obj": page_obj})
        rendered = template.render(context)

        assert "?page=2" in rendered

    def test_missing_args(self):
        with pytest.raises(TemplateSyntaxError):
            Template(
                """{% pagination %}
                <span>{{ item }}</span>
            {% endpagination %}"""
            )
