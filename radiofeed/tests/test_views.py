import pytest
from django.conf import settings
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from pytest_django.asserts import assertTemplateUsed

from radiofeed.cover_image import CoverImageError, get_cover_image_url
from radiofeed.tests.asserts import assert200, assert404


class TestErrorPages:
    @pytest.mark.parametrize(
        "template_name",
        [
            pytest.param("400.html"),
            pytest.param("403.html"),
            pytest.param("403_csrf.html"),
            pytest.param("405.html"),
            pytest.param("429.html"),
            pytest.param("500.html"),
        ],
    )
    def test_render_page(self, rf, anonymous_user, template_name):
        req = rf.get("/")
        req.user = anonymous_user
        response = TemplateResponse(req, template_name)
        assert b"Error" in response.render().content


class TestIndex:
    url = reverse_lazy("index")

    @pytest.mark.django_db
    def test_anonymous(self, client):
        response = client.get(self.url)
        assert200(response)
        assertTemplateUsed(response, "index.html")

    @pytest.mark.django_db
    def test_authenticated(self, client, auth_user):
        response = client.get(self.url)
        assert response.url == settings.LOGIN_REDIRECT_URL


class TestManifest:
    @pytest.mark.django_db
    def test_get(self, client):
        response = client.get(reverse("manifest"))
        assert200(response)


class TestAssetlinks:
    @pytest.mark.django_db
    def test_get(self, client):
        response = client.get(reverse("assetlinks"))
        assert200(response)


class TestRobots:
    @pytest.mark.django_db
    def test_get(self, client):
        response = client.get(reverse("robots"))
        assert200(response)


class TestSecurty:
    @pytest.mark.django_db
    def test_get(self, client):
        response = client.get(reverse("security"))
        assert200(response)


class TestAbout:
    @pytest.mark.django_db
    def test_get(self, client):
        response = client.get(reverse("about"))
        assert200(response)


class TestPrivacy:
    @pytest.mark.django_db
    def test_get(self, client):
        response = client.get(reverse("privacy"))
        assert200(response)


class TestAcceptCookies:
    @pytest.mark.django_db
    def test_post(self, client):
        response = client.post(reverse("accept_cookies"))
        assert200(response)
        assert "accept-cookies" in response.cookies


class TestCoverImage:
    cover_url = "http://example.com/test.png"

    @pytest.mark.django_db
    def test_ok(self, client, mocker):
        mocker.patch("radiofeed.views.fetch_cover_image", return_value=b"ok")
        response = client.get(get_cover_image_url(self.cover_url, 96))
        assert200(response)

    @pytest.mark.django_db
    def test_invalid_image(self, client, mocker):
        mocker.patch("radiofeed.views.fetch_cover_image", side_effect=CoverImageError())
        response = client.get(get_cover_image_url(self.cover_url, 96))
        assert200(response)

    @pytest.mark.django_db
    def test_not_accepted_size(self, client):
        response = client.get(get_cover_image_url(self.cover_url, 500))
        assert404(response)

    @pytest.mark.django_db
    def test_missing_url(self, client, mocker):
        response = client.get(
            f"{reverse('cover_image', kwargs={'size': 96})}",
        )
        assert404(response)

    @pytest.mark.django_db
    def test_unsigned_url(self, client, mocker):
        response = client.get(
            f"{reverse('cover_image', kwargs={'size': 96})}",
            {"url": "test.jpg"},
        )
        assert404(response)
