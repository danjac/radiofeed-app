import http
import urllib.parse

import httpx
import pytest
from django.conf import settings
from django.core.signing import Signer
from django.template.response import TemplateResponse
from django.urls import reverse, reverse_lazy
from pytest_django import assertTemplateUsed

from radiofeed.http_client import Client


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
    def test_render_page(self, rf, template_name):
        response = TemplateResponse(rf.get("/"), template_name)
        assert b"Error" in response.render().content


class TestIndex:
    url = reverse_lazy("index")

    @pytest.mark.django_db
    def test_anonymous(self, client):
        response = client.get(self.url)
        assert response.status_code == http.HTTPStatus.OK
        assertTemplateUsed(response, "index.html")

    @pytest.mark.django_db
    def test_authenticated(self, client, auth_user):
        response = client.get(self.url)
        assert response.url == settings.LOGIN_REDIRECT_URL


class TestManifest:
    @pytest.mark.django_db
    def test_get(self, client):
        response = client.get(reverse("manifest"))
        assert response.status_code == http.HTTPStatus.OK


class TestAssetlinks:
    @pytest.mark.django_db
    def test_get(self, client):
        response = client.get(reverse("assetlinks"))
        assert response.status_code == http.HTTPStatus.OK


class TestServiceWorker:
    @pytest.mark.django_db
    def test_get(self, client):
        response = client.get(reverse("service_worker"))
        assert response.status_code == http.HTTPStatus.OK


class TestFavicon:
    @pytest.mark.django_db
    def test_get(self, client):
        response = client.get(reverse("favicon"))
        assert response.status_code == http.HTTPStatus.OK


class TestRobots:
    @pytest.mark.django_db
    def test_get(self, client):
        response = client.get(reverse("robots"))
        assert response.status_code == http.HTTPStatus.OK


class TestSecurty:
    @pytest.mark.django_db
    def test_get(self, client):
        response = client.get(reverse("security"))
        assert response.status_code == http.HTTPStatus.OK


class TestAbout:
    @pytest.mark.django_db
    def test_get(self, client):
        response = client.get(reverse("about"))
        assert response.status_code == http.HTTPStatus.OK


class TestPrivacy:
    @pytest.mark.django_db
    def test_get(self, client):
        response = client.get(reverse("privacy"))
        assert response.status_code == http.HTTPStatus.OK


class TestAcceptGdprCookies:
    @pytest.mark.django_db
    def test_post(self, client):
        response = client.post(reverse("accept_gdpr_cookies"))
        assert response.status_code == http.HTTPStatus.OK
        assert "accept-cookies" in response.cookies


class TestCoverImage:
    cover_url = "http://example.com/test.png"

    def get_url(self, size, url):
        return (
            reverse("cover_image", kwargs={"size": size})
            + "?"
            + urllib.parse.urlencode({"url": url})
        )

    def encode_url(self, url):
        return Signer().sign(url)

    @pytest.mark.django_db
    def test_ok(self, client, db, mocker):
        def _handler(request):
            return httpx.Response(http.HTTPStatus.OK, content=b"")

        mock_client = Client(transport=httpx.MockTransport(_handler))
        mocker.patch("radiofeed.views.get_client", return_value=mock_client)
        mocker.patch("PIL.Image.open", return_value=mocker.Mock())
        response = client.get(self.get_url(96, self.encode_url(self.cover_url)))
        assert response.status_code == http.HTTPStatus.OK

    @pytest.mark.django_db
    def test_not_accepted_size(self, client, db, mocker):
        response = client.get(self.get_url(500, self.encode_url(self.cover_url)))
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    @pytest.mark.django_db
    def test_missing_url_param(self, client, db, mocker):
        response = client.get(reverse("cover_image", kwargs={"size": 100}))
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    @pytest.mark.django_db
    def test_unsigned_url(self, client, db):
        response = client.get(self.get_url(96, self.cover_url))
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    @pytest.mark.django_db
    def test_failed_download(self, client, db, mocker):
        def _handler(request):
            raise httpx.HTTPError("invalid")

        mock_client = Client(transport=httpx.MockTransport(_handler))
        mocker.patch("radiofeed.views.get_client", return_value=mock_client)

        response = client.get(self.get_url(96, self.encode_url(self.cover_url)))
        assert response.status_code == http.HTTPStatus.OK

    @pytest.mark.django_db
    def test_failed_process(self, client, db, mocker):
        def _handler(request):
            return httpx.Response(http.HTTPStatus.OK, content=b"")

        mock_client = Client(transport=httpx.MockTransport(_handler))
        mocker.patch("radiofeed.views.get_client", return_value=mock_client)
        mocker.patch("PIL.Image.open", side_effect=IOError())
        response = client.get(self.get_url(96, self.encode_url(self.cover_url)))
        assert response.status_code == http.HTTPStatus.OK
