import pytest

from radiofeed import cover_images


class TestGetPlaceholderUrl:
    @pytest.mark.parametrize(
        ("size", "expected"),
        [
            pytest.param(size, f"/static/img/placeholder-{size}.webp", id=f"{size}px")
            for size in cover_images.COVER_IMAGE_SIZES
        ],
    )
    def test_check_paths(self, size, expected):
        assert cover_images.get_placeholder_path(size).exists()


class TestGetCoverImageAttrs:
    @pytest.mark.parametrize(
        ("variant", "expected"),
        [
            pytest.param(
                cover_images.CoverImageVariant.CARD,
                {
                    "height": 96,
                    "width": 96,
                    "src": "/covers/96/cover.webp?url=test.jpg",
                },
                id="card",
            ),
            pytest.param(
                cover_images.CoverImageVariant.DETAIL,
                {
                    "height": 160,
                    "width": 160,
                    "src": "/covers/160/cover.webp?url=test.jpg",
                    "sizes": "(max-width: 1023.99px) 144px, (min-width: 1024px) 160px",
                },
                id="detail",
            ),
            pytest.param(
                cover_images.CoverImageVariant.TILE,
                {
                    "height": 224,
                    "width": 224,
                    "src": "/covers/224/cover.webp?url=test.jpg",
                    "sizes": "(max-width: 1023.99px) 112px, (min-width: 1024px) 224px",
                },
                id="tile",
            ),
        ],
    )
    def test_get_cover_image_attrs(self, variant, expected):
        attrs = cover_images.get_cover_image_attrs("test.jpg", variant)
        assert attrs["height"] == expected["height"]
        assert attrs["width"] == expected["width"]
        assert attrs["src"].startswith(expected["src"])

        if "sizes" in expected:
            assert attrs["sizes"] == expected["sizes"]
        else:
            assert "sizes" not in attrs
