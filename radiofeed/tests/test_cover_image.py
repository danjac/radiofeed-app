import pytest

from radiofeed.cover_image import (
    CoverImageVariant,
    get_cover_image_attrs,
    get_cover_image_sizes,
    get_placeholder_path,
)


class TestGetPlaceholderUrl:
    @pytest.mark.parametrize(
        ("size", "expected"),
        [
            pytest.param(size, f"/static/img/placeholder-{size}.webp", id=f"{size}px")
            for size in get_cover_image_sizes()
        ],
    )
    def test_check_paths(self, size, expected):
        assert get_placeholder_path(size).exists()


class TestGetCoverImageAttrs:
    @pytest.mark.parametrize(
        ("variant", "expected"),
        [
            pytest.param(
                CoverImageVariant.CARD,
                {
                    "height": 96,
                    "width": 96,
                    "src": "/covers/96/cover.webp?url=test.jpg",
                },
                id="card",
            ),
            pytest.param(
                CoverImageVariant.DETAIL,
                {
                    "height": 160,
                    "width": 160,
                    "src": "/covers/160/cover.webp?url=test.jpg",
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
