import pytest
from django.contrib.sites.models import Site
from django.template.context import RequestContext
from django.test import override_settings
from django.urls import reverse, reverse_lazy

from radiofeed.defaulttags import (
    absolute_uri,
    active_link,
    cover_image,
    format_duration,
    markdown,
)


@pytest.fixture()
def req(rf, anonymous_user):
    req = rf.get("/")
    req.user = anonymous_user
    req.htmx = False
    req.site = Site.objects.get_current()
    return req


@pytest.fixture()
def auth_req(req, user):
    req.user = user
    return req


class TestFormatDuration:
    @pytest.mark.parametrize(
        ("duration", "expected"),
        [
            pytest.param(None, "", id="none"),
            pytest.param(0, "", id="zero"),
            pytest.param(30, "", id="30 seconds"),
            pytest.param(540, "9min", id="9 minutes"),
            pytest.param(2400, "40min", id="40 minutes"),
            pytest.param(9000, "2h 30min", id="2 hours 30 minutes"),
        ],
    )
    def test_format_duration(self, duration, expected):
        assert format_duration(duration) == expected


class TestCoverImage:
    def test_is_cover_url(self):
        dct = cover_image("https://example.com/test.jpg", 100, "test img")
        assert "test.jpg" in dct["cover_url"]
        assert dct["placeholder"] == "/static/img/placeholder-100.webp"

    def test_is_not_cover_url(self):
        dct = cover_image("", 100, "test img")
        assert dct["cover_url"] == ""
        assert dct["placeholder"] == "/static/img/placeholder-100.webp"

    def test_invalid_cover_image_size(self):
        with pytest.raises(AssertionError, match=r"invalid cover image size:500"):
            cover_image("https://example.com/test.jpg", 500, "test img")


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
            pytest.param(None, "", id="none"),
            pytest.param("", "", id="empty"),
            pytest.param("test", "<p>test</p>\n", id="text"),
            pytest.param("   ", "", id="space"),
            pytest.param("<p>test</p>", "<p>test</p>", id="html"),
            pytest.param("<p>test</p>   ", "<p>test</p>", id="html and spaces"),
            pytest.param("<script>test</script>", "", id="unsafe html"),
        ],
    )
    def test_markdown(self, value, expected):
        assert markdown(value) == {"content": expected}


class TestAbsoluteUri:
    @pytest.mark.django_db()
    def test_plain_url(self):
        assert absolute_uri("/podcasts/") == "http://example.com/podcasts/"

    @pytest.mark.django_db()
    @override_settings(USE_HTTPS=True)
    def test_https(self):
        assert absolute_uri("/podcasts/") == "https://example.com/podcasts/"

    @pytest.mark.django_db()
    def test_object(self, podcast):
        assert (
            absolute_uri(podcast) == f"http://example.com{podcast.get_absolute_url()}"
        )
