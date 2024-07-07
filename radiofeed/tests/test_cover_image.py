import pytest

from radiofeed import cover_image


class TestGetPlaceholderUrl:
    @pytest.mark.parametrize(
        ("size", "expected"),
        [
            pytest.param(size, f"/static/img/placeholder-{size}.webp", id=str(size))
            for size in cover_image.COVER_IMAGE_SIZES
        ],
    )
    def test_check_paths(self, settings, size, expected):
        settings.STATIC_URL = "/static/"
        assert cover_image.get_placeholder_url(size) == expected


class TestGetCoverImageAttrs:
    @pytest.mark.parametrize(
        ("size", "expected"),
        [
            pytest.param(
                "sm",
                {
                    "height": 96,
                    "width": 96,
                    "src": "/covers/96/cover.webp?url=test.jpg",
                    "sizes": "(max-width: 1023.99px) 64px, (min-width: 1024px) 96px",
                },
                id="sm",
            ),
            pytest.param(
                "md",
                {
                    "height": 180,
                    "width": 180,
                    "src": "/covers/180/cover.webp?url=test.jpg",
                    "sizes": "(max-width: 1023.99px) 128px, (min-width: 1024px) 180px",
                },
                id="md",
            ),
            pytest.param(
                "lg",
                {
                    "height": 240,
                    "width": 240,
                    "src": "/covers/240/cover.webp?url=test.jpg",
                    "sizes": "(max-width: 1023.99px) 180px, (min-width: 1024px) 240px",
                },
                id="lg",
            ),
        ],
    )
    def test_get_cover_image_attrs(self, size, expected):
        attrs = cover_image.get_cover_image_attrs("test.jpg", size)
        assert attrs["height"] == expected["height"]
        assert attrs["sizes"] == expected["sizes"]
        assert attrs["width"] == expected["width"]
        assert attrs["src"].startswith(expected["src"])
