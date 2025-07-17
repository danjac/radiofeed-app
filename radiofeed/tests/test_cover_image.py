import contextlib
import io

import httpx
import pytest

from radiofeed.cover_image import (
    CoverImageError,
    CoverImageTooLargeError,
    fetch_cover_image,
    get_cover_image_attrs,
    get_cover_image_class,
    get_cover_image_sizes,
    get_cover_image_url,
    get_metadata_info,
    get_placeholder_path,
    get_placeholder_url,
    save_cover_image,
)
from radiofeed.http_client import Client


class TestFetchCoverImage:
    cover_url = "https://example.com/test.jpg"

    def test_ok(self, mocker):
        def _handler(request):
            return httpx.Response(200)

        client = Client(transport=httpx.MockTransport(_handler))
        assert fetch_cover_image(client, self.cover_url)

    def test_content_length_ok(self, mocker):
        def _handler(request):
            return httpx.Response(200, headers={"Content-Length": "123"})

        client = Client(transport=httpx.MockTransport(_handler))
        assert fetch_cover_image(client, self.cover_url)

    def test_content_length_invalid(self, mocker):
        def _handler(request):
            return httpx.Response(200, headers={"Content-Length": "invalid"})

        client = Client(transport=httpx.MockTransport(_handler))
        assert fetch_cover_image(client, self.cover_url)

    def test_chunked_content_too_long(self, mocker, settings):
        settings.COVER_IMAGE_MAX_SIZE = 100

        # mock entire fetch
        client = mocker.Mock()

        client.head.return_value = httpx.Response(200)

        mock_response = mocker.Mock()

        mock_response.iter_bytes.return_value = [b"OK"]

        @contextlib.contextmanager
        def mock_stream(*args, **kwargs):
            yield mock_response

        client.stream = mock_stream

        mock_bytesio = mocker.Mock()
        mock_bytesio.tell.return_value = 200

        mocker.patch("radiofeed.cover_image.io.BytesIO", return_value=mock_bytesio)

        with pytest.raises(CoverImageTooLargeError):
            fetch_cover_image(client, self.cover_url)

    def test_content_length_too_long(self, mocker, settings):
        settings.COVER_IMAGE_MAX_SIZE = 100

        def _handler(request):
            return httpx.Response(200, headers={"Content-Length": "200"})

        client = Client(transport=httpx.MockTransport(_handler))
        with pytest.raises(CoverImageTooLargeError):
            fetch_cover_image(client, self.cover_url)

    def test_http_error(self, mocker):
        def _handler(request):
            raise httpx.HTTPError("invalid")

        client = Client(transport=httpx.MockTransport(_handler))
        with pytest.raises(CoverImageError):
            fetch_cover_image(client, self.cover_url)


class TestSaveCoverImage:
    def test_ok(self, mocker, settings):
        settings.COVER_IMAGE_MAX_SIZE = 16 * 1024 * 1024  # 1 MB

        mock_image = mocker.Mock()
        mock_image.format = "png"
        mock_image.mode = "RGBA"
        mock_image.size = (100, 100)

        @contextlib.contextmanager
        def get_mock_image(*args, **kwargs):
            yield mock_image

        mocker.patch("radiofeed.cover_image.Image.open", get_mock_image)

        save_cover_image(io.BytesIO(), io.BytesIO(), size=100)

    def test_too_large(self, mocker, settings):
        settings.COVER_IMAGE_MAX_SIZE = 1 * 1024 * 1024  # 1 MB

        mock_image = mocker.Mock()
        mock_image.format = "png"
        mock_image.mode = "RGBA"
        mock_image.size = (10000, 10000)

        @contextlib.contextmanager
        def get_mock_image(*args, **kwargs):
            yield mock_image

        mocker.patch("radiofeed.cover_image.Image.open", get_mock_image)

        with pytest.raises(CoverImageError):
            save_cover_image(io.BytesIO(), io.BytesIO(), size=100)

    def test_error(self, mocker):
        mocker.patch("radiofeed.cover_image.Image.open", side_effect=OSError())
        with pytest.raises(CoverImageError):
            save_cover_image(io.BytesIO(), io.BytesIO(), size=100)


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
