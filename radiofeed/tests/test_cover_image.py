import contextlib

import httpx
import pytest
from PIL.Image import UnidentifiedImageError

from radiofeed.client import Client
from radiofeed.cover_image import (
    CoverImageError,
    CoverImageTooLargeError,
    decode_cover_url,
    encode_cover_url,
    fetch_cover_image,
    get_cover_image_attrs,
    get_cover_image_sizes,
    get_cover_image_url,
    get_metadata_info,
    get_placeholder_path,
    get_placeholder_url,
    save_cover_image,
)


class TestEncodeDecodeCoverUrl:
    def test_url(self):
        url = "https://example.com/test.jpg"
        encoded = encode_cover_url(url)
        decoded = decode_cover_url(encoded)
        assert decoded == url


class TestFetchCoverImage:
    cover_url = "https://example.com/test.jpg"

    @pytest.fixture
    def mock_image(self, mocker):
        mock_image = mocker.Mock()

        mock_image.size = (1000, 1000)
        mock_image.format = "png"
        mock_image.mode = "RGBA"

        mock_image.resize.return_value = mocker.Mock()

        mocker.patch("radiofeed.cover_image.Image.open", return_value=mock_image)

        return mock_image

    def test_ok(self, mock_image):
        def _handler(request):
            return httpx.Response(200)

        client = Client(transport=httpx.MockTransport(_handler))
        assert fetch_cover_image(client, self.cover_url, 200)

    def test_content_length_ok(self, mock_image):
        def _handler(request):
            return httpx.Response(200, headers={"Content-Length": "123"})

        client = Client(transport=httpx.MockTransport(_handler))
        assert fetch_cover_image(client, self.cover_url, 200)

    def test_content_length_invalid(self, mock_image):
        def _handler(request):
            return httpx.Response(200, headers={"Content-Length": "invalid"})

        client = Client(transport=httpx.MockTransport(_handler))
        assert fetch_cover_image(client, self.cover_url, 200)

    def test_chunked_content_too_long(self, mocker):
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
        mock_bytesio.tell.return_value = 100_000_000_000

        mocker.patch("radiofeed.cover_image.io.BytesIO", return_value=mock_bytesio)

        with pytest.raises(CoverImageTooLargeError):
            fetch_cover_image(client, self.cover_url, 200)

    def test_content_length_too_long(self):
        def _handler(request):
            return httpx.Response(
                200,
                headers={
                    "Content-Length": str(100_000_000_000),
                },
            )

        client = Client(transport=httpx.MockTransport(_handler))
        with pytest.raises(CoverImageTooLargeError):
            fetch_cover_image(client, self.cover_url, 200)

    def test_too_many_pixels(self, mock_image):
        def _handler(request):
            return httpx.Response(200)

        mock_image.size = (10_000_000, 10_000_000)

        client = Client(transport=httpx.MockTransport(_handler))
        with pytest.raises(CoverImageTooLargeError):
            fetch_cover_image(client, self.cover_url, 200)

    def test_http_error(self):
        def _handler(request):
            raise httpx.HTTPError("invalid")

        client = Client(transport=httpx.MockTransport(_handler))
        with pytest.raises(CoverImageError):
            fetch_cover_image(client, self.cover_url, 200)

    def test_image_invalid(self, mocker):
        def _handler(request):
            return httpx.Response(200)

        client = Client(transport=httpx.MockTransport(_handler))

        mocker.patch(
            "radiofeed.cover_image.Image.open", side_effect=UnidentifiedImageError()
        )

        with pytest.raises(CoverImageError):
            fetch_cover_image(client, self.cover_url, 200)


class TestSaveCoverImage:
    def test_ok(self, mocker, settings):
        settings.COVER_IMAGE_MAX_SIZE = 16 * 1024 * 1024  # 1 MB

        mock_image = mocker.Mock()

        @contextlib.contextmanager
        def get_mock_image(*args, **kwargs):
            yield mock_image

        save_cover_image(mock_image)
        mock_image.save.assert_called()

    def test_error(self, mocker):
        mock_image = mocker.Mock()
        mock_image.save.side_effect = OSError("invalid")

        with pytest.raises(CoverImageError):
            save_cover_image(mock_image)


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
