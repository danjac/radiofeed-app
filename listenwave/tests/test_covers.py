import contextlib
import io

import httpx
import pytest
from PIL import Image

from listenwave.covers import (
    CoverFetchError,
    CoverProcessError,
    CoverSaveError,
    decode_url,
    encode_url,
    fetch_image,
    get_cover_sizes,
    get_cover_url,
    get_image_attrs,
    get_metadata_info,
    get_placeholder_path,
    get_placeholder_url,
    process_image,
    save_image,
)
from listenwave.http_client import Client


class TestEncodeDecodeCoverUrl:
    def test_url(self):
        url = "https://example.com/test.jpg"
        encoded = encode_url(url)
        decoded = decode_url(encoded)
        assert decoded == url


class TestFetchImage:
    cover_url = "https://example.com/test.jpg"

    def test_ok(self):
        def _handler(request):
            return httpx.Response(200)

        client = Client(transport=httpx.MockTransport(_handler))
        assert fetch_image(client, self.cover_url)

    def test_content_length_ok(self):
        def _handler(request):
            return httpx.Response(200, headers={"Content-Length": "123"})

        client = Client(transport=httpx.MockTransport(_handler))
        assert fetch_image(client, self.cover_url)

    def test_content_length_invalid(self):
        def _handler(request):
            return httpx.Response(200, headers={"Content-Length": "invalid"})

        client = Client(transport=httpx.MockTransport(_handler))
        assert fetch_image(client, self.cover_url)

    def test_chunked_content_too_long(self, mocker):
        # mock entire fetch
        client = mocker.Mock()

        mock_response = mocker.Mock()
        mock_response.headers = {"content-length": 20000}

        mock_response.iter_bytes.return_value = [b"OK"]

        @contextlib.contextmanager
        def mock_stream(*args, **kwargs):
            yield mock_response

        client.stream = mock_stream

        mock_bytesio = mocker.Mock()
        mock_bytesio.tell.return_value = 100_000_000_000

        mocker.patch("listenwave.covers.io.BytesIO", return_value=mock_bytesio)

        with pytest.raises(CoverFetchError):
            fetch_image(client, self.cover_url)

    def test_content_length_too_long(self):
        def _handler(request):
            return httpx.Response(
                200,
                headers={
                    "Content-Length": str(100_000_000_000),
                },
            )

        client = Client(transport=httpx.MockTransport(_handler))
        with pytest.raises(CoverFetchError):
            fetch_image(client, self.cover_url)

    def test_http_error(self):
        def _handler(request):
            raise httpx.HTTPError("invalid")

        client = Client(transport=httpx.MockTransport(_handler))
        with pytest.raises(CoverFetchError):
            fetch_image(client, self.cover_url)


class TestProcessImage:
    @pytest.fixture
    def mock_image(self, mocker):
        """Create a mock PIL Image object."""
        mock = mocker.MagicMock(spec=Image.Image)
        mock.size = (800, 600)
        mock.format = "JPEG"
        mock.mode = "RGB"
        mocker.patch("PIL.Image.open", return_value=mock)
        return mock

    @pytest.fixture
    def resized_mock_image(self, mocker):
        """Create a mock resized PIL Image object."""
        mock = mocker.MagicMock(spec=Image.Image)
        mock.size = (200, 200)
        return mock

    def test_too_many_pixels(self, mock_image):
        """Test that images exceeding max pixel count raise error."""
        mock_image.size = (100000, 100000)  # 10 billion pixels

        with pytest.raises(CoverProcessError):
            process_image(io.BytesIO(b"fake data"), 200)

    def test_successful_resize(self, mock_image, resized_mock_image):
        """Test successful image resize."""
        mock_image.resize.return_value = resized_mock_image

        result = process_image(io.BytesIO(b"fake data"), 300)

        assert result == resized_mock_image
        mock_image.resize.assert_called_once_with((300, 300), Image.Resampling.LANCZOS)

    def test_invalid_image_format(self, mocker):
        """Test that unidentifiable images raise error."""
        mocker.patch(
            "PIL.Image.open",
            side_effect=Image.UnidentifiedImageError("Cannot identify"),
        )

        with pytest.raises(CoverProcessError):
            process_image(io.BytesIO(b"invalid"), 200)

    def test_corrupted_image_data(self, mocker):
        """Test that corrupted images raise error."""
        mocker.patch("PIL.Image.open", side_effect=OSError("image file is truncated"))

        with pytest.raises(CoverProcessError):
            process_image(io.BytesIO(b"corrupted"), 200)

    def test_resize_with_invalid_size_type(self, mock_image):
        """Test that invalid size type raises error."""
        mock_image.resize.side_effect = TypeError("size must be tuple")

        with pytest.raises(CoverProcessError):
            process_image(io.BytesIO(b"data"), 200)

    def test_resize_with_invalid_resampling(self, mock_image):
        """Test that invalid resampling filter raises error."""
        mock_image.resize.side_effect = ValueError("invalid resampling filter")

        with pytest.raises(CoverProcessError):
            process_image(io.BytesIO(b"data"), 200)

    def test_small_image_upscaling(self, mock_image, resized_mock_image):
        """Test that small images can be upscaled."""
        mock_image.size = (50, 50)
        mock_image.resize.return_value = resized_mock_image

        result = process_image(io.BytesIO(b"data"), 300)

        assert result == resized_mock_image
        mock_image.resize.assert_called_once_with((300, 300), Image.Resampling.LANCZOS)

    def test_downscaling_large_image(self, mock_image, resized_mock_image):
        """Test downscaling a larger image."""
        mock_image.size = (1000, 1000)
        mock_image.resize.return_value = resized_mock_image

        result = process_image(io.BytesIO(b"data"), 200)

        assert result == resized_mock_image
        mock_image.resize.assert_called_once_with((200, 200), Image.Resampling.LANCZOS)

    def test_exact_size_image(self, mock_image, resized_mock_image):
        """Test that image already at target size still gets processed."""
        mock_image.size = (200, 200)
        mock_image.resize.return_value = resized_mock_image

        result = process_image(io.BytesIO(b"data"), 200)

        assert result == resized_mock_image
        mock_image.resize.assert_called_once_with((200, 200), Image.Resampling.LANCZOS)

    def test_different_formats(self, mock_image, resized_mock_image):
        """Test processing different image formats."""
        mock_image.resize.return_value = resized_mock_image

        for format_type in ["PNG", "JPEG", "BMP"]:
            mock_image.format = format_type

            result = process_image(io.BytesIO(b"data"), 250)

            assert result == resized_mock_image
            mock_image.resize.assert_called_with((250, 250), Image.Resampling.LANCZOS)

    def test_rgba_image(self, mock_image, resized_mock_image):
        """Test processing image with alpha channel."""
        mock_image.mode = "RGBA"
        mock_image.size = (500, 500)
        mock_image.resize.return_value = resized_mock_image

        result = process_image(io.BytesIO(b"data"), 300)

        assert result == resized_mock_image
        mock_image.resize.assert_called_once_with((300, 300), Image.Resampling.LANCZOS)

    def test_grayscale_image(self, mock_image, resized_mock_image):
        """Test processing grayscale image."""
        mock_image.mode = "L"
        mock_image.size = (600, 600)
        mock_image.resize.return_value = resized_mock_image

        result = process_image(io.BytesIO(b"data"), 400)

        assert result == resized_mock_image
        mock_image.resize.assert_called_once_with((400, 400), Image.Resampling.LANCZOS)


class TestSaveImage:
    def test_ok(self, mocker, settings):
        settings.COVER_IMAGE_MAX_SIZE = 16 * 1024 * 1024  # 1 MB

        mock_image = mocker.Mock()

        save_image(mock_image)
        mock_image.save.assert_called()

    def test_error(self, mocker):
        mock_image = mocker.Mock()
        mock_image.save.side_effect = OSError("invalid")

        with pytest.raises(CoverSaveError):
            save_image(mock_image)


class TestGetMetadataInfo:
    def test_build_info(self, rf):
        req = rf.get("/")
        metadata = get_metadata_info(req, "test.jpg")
        assert len(metadata) == 4


class TestGetPlaceholderPath:
    @pytest.mark.parametrize(
        "size",
        [pytest.param(size, id=f"{size}px") for size in get_cover_sizes()],
    )
    def test_check_paths(self, size):
        assert get_placeholder_path(size).exists()


class TestGetPlaceholderUrl:
    @pytest.mark.parametrize(
        "size",
        [pytest.param(size, id=f"{size}px") for size in get_cover_sizes()],
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
    def test_get_image_attrs(self, variant, expected):
        attrs = get_image_attrs(variant, "test.jpg", "test pic")
        assert attrs["height"] == expected["height"]
        assert attrs["width"] == expected["width"]
        assert attrs["alt"] == "test pic"
        assert attrs["title"] == "test pic"
        assert attrs["src"] == get_cover_url("test.jpg", expected["size"])

        if "sizes" in expected:
            assert attrs["sizes"] == expected["sizes"]
        else:
            assert "sizes" not in attrs
