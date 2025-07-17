import httpx
import pytest

from radiofeed.cover_image import (
    fetch_cover_image,
    get_cover_image_attrs,
    get_cover_image_class,
    get_cover_image_sizes,
    get_cover_image_url,
    get_metadata_info,
    get_placeholder_path,
    get_placeholder_url,
)
from radiofeed.http_client import Client


class TestFetchCoverImage:
    """
      @pytest.mark.django_db
    -    def test_failed_download(self, client, mocker):
    -        def _handler(_):
    -            raise httpx.HTTPError("invalid")
    -
    -        mock_client = Client(transport=httpx.MockTransport(_handler))
    -        mocker.patch("radiofeed.views.get_client", return_value=mock_client)
    -
    -        response = client.get(get_cover_image_url(self.cover_url, 96))
    -        assert200(response)
    """

    def test_ok(self, mocker):
        def _handler(request):
            return httpx.Response(200)

        client = Client(transport=httpx.MockTransport(_handler))
        mock_image = mocker.patch(
            "radiofeed.cover_image.Image.open", return_value=b"ok"
        )
        assert fetch_cover_image(client, "test.jpg", 96)
        mock_image.assert_called()

    def test_content_length_ok(self, mocker):
        def _handler(request):
            return httpx.Response(200, headers={"Content-Length": "123"})

        client = Client(transport=httpx.MockTransport(_handler))
        mock_image = mocker.patch(
            "radiofeed.cover_image.Image.open", return_value=b"ok"
        )
        assert fetch_cover_image(client, "test.jpg", 96)
        mock_image.assert_called()

    def test_content_length_too_long(self, mocker, settings):
        settings.COVER_IMAGE_MAX_SIZE = 100

        def _handler(request):
            return httpx.Response(200, headers={"Content-Length": "200"})

        client = Client(transport=httpx.MockTransport(_handler))
        mock_image = mocker.patch(
            "radiofeed.cover_image.Image.open", return_value=b"ok"
        )
        assert fetch_cover_image(client, "test.jpg", 96)
        mock_image.assert_not_called()

    def test_http_error(self, mocker):
        def _handler(request):
            raise httpx.HTTPError("invalid")

        client = Client(transport=httpx.MockTransport(_handler))
        mock_image = mocker.patch(
            "radiofeed.cover_image.Image.open", return_value=b"ok"
        )
        assert fetch_cover_image(client, "test.jpg", 96)
        mock_image.assert_not_called()


class TestGetMetadataInfo:
    def test_build_info(self, rf):
        req = rf.get("/")
        metadata = get_metadata_info(req, "test.jpg")
        assert len(metadata) == 4


class TestGetPlaceholderPath:
    @pytest.mark.parametrize(
        "size",
        [pytest.param(size, id=f"{size}px") for size in get_cover_image_sizes()],
    )
    def test_check_paths(self, size):
        assert get_placeholder_path(size).exists()


class TestGetPlaceholderUrl:
    @pytest.mark.parametrize(
        "size",
        [pytest.param(size, id=f"{size}px") for size in get_cover_image_sizes()],
    )
    def test_check_url(self, size):
        assert get_placeholder_url(size).endswith(f"{size}.webp")


class TestGetCoverImageAttrs:
    @pytest.mark.parametrize(
        ("variant", "expected"),
        [
            pytest.param(
                "card",
                {
                    "height": 96,
                    "width": 96,
                    "size": 96,
                },
                id="card",
            ),
            pytest.param(
                "detail",
                {
                    "height": 160,
                    "width": 160,
                    "sizes": "(max-width: 1023.99px) 144px, (min-width: 1024px) 160px",
                    "size": 160,
                },
                id="detail",
            ),
        ],
    )
    def test_get_cover_image_attrs(self, variant, expected):
        attrs = get_cover_image_attrs(variant, "test.jpg", "test pic")
        assert attrs["height"] == expected["height"]
        assert attrs["width"] == expected["width"]
        assert attrs["alt"] == "test pic"
        assert attrs["title"] == "test pic"
        assert attrs["src"] == get_cover_image_url("test.jpg", expected["size"])

        if "sizes" in expected:
            assert attrs["sizes"] == expected["sizes"]
        else:
            assert "sizes" not in attrs


class TestCoverImageClass:
    def test_get_cover_image_class(self):
        assert get_cover_image_class("card", "object-cover") == "size-16 object-cover"

    def test_remove_duplicates(self):
        assert (
            get_cover_image_class("card", "object-cover size-16")
            == "size-16 object-cover"
        )
