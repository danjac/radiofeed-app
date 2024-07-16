import pytest

from radiofeed import cover_image


class TestGetPlaceholderUrl:
    @pytest.mark.parametrize(
        ("size", "expected"),
        [
            pytest.param(size, f"/static/img/placeholder-{size}.webp", id=f"{size}px")
            for size in cover_image.COVER_IMAGE_SIZES
        ],
    )
    def test_check_paths(self, size, expected):
        assert cover_image.get_placeholder_path(size).exists()


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
                },
                id="sm",
            ),
            pytest.param(
                "md",
                {
                    "height": 160,
                    "width": 160,
                    "src": "/covers/160/cover.webp?url=test.jpg",
                    "sizes": "(max-width: 1023.99px) 144px, (min-width: 1024px) 160px",
                },
                id="md",
            ),
            pytest.param(
                "lg",
                {
                    "height": 224,
                    "width": 224,
                    "src": "/covers/224/cover.webp?url=test.jpg",
                    "sizes": "(max-width: 1023.99px) 112px, (min-width: 1024px) 224px",
                },
                id="lg",
            ),
        ],
    )
    def test_get_cover_image_attrs(self, size, expected):
        attrs = cover_image.get_cover_image_attrs("test.jpg", size)
        assert attrs["height"] == expected["height"]
        assert attrs["width"] == expected["width"]
        assert attrs["src"].startswith(expected["src"])

        if "sizes" in expected:
            assert attrs["sizes"] == expected["sizes"]
        else:
            assert "sizes" not in attrs
