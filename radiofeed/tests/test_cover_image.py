import pytest

from radiofeed.cover_image import (
    InvalidCoverUrlError,
    decrypt_cover_url,
    encrypt_cover_url,
    get_cover_image_attrs,
    get_cover_image_sizes,
    get_metadata_info,
    get_placeholder_path,
    get_placeholder_url,
)


class TestEncryptDecryptCoverUrl:
    def test_encrypt_decrypt(self):
        cover_url = "https://example.com/test.jpg"
        encrypted_url = encrypt_cover_url(cover_url)
        decrypted_url = decrypt_cover_url(encrypted_url)
        assert decrypted_url == cover_url

    def test_invalid_encrypted_url(self):
        with pytest.raises(InvalidCoverUrlError):
            decrypt_cover_url("test.jpg")


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
                    "src": "/covers/96/cover.webp?",
                },
                id="card",
            ),
            pytest.param(
                "detail",
                {
                    "height": 160,
                    "width": 160,
                    "src": "/covers/160/cover.webp?",
                    "sizes": "(max-width: 1023.99px) 144px, (min-width: 1024px) 160px",
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
        assert attrs["src"].startswith(expected["src"])

        if "sizes" in expected:
            assert attrs["sizes"] == expected["sizes"]
        else:
            assert "sizes" not in attrs
