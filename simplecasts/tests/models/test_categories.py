import pytest

from simplecasts.models import (
    Category,
)
from simplecasts.tests.factories import (
    CategoryFactory,
)


class TestCategoryModel:
    def test_str(self):
        category = Category(name="Testing")
        assert str(category) == "Testing"

    @pytest.mark.django_db
    def test_slug(self):
        category = CategoryFactory(name="Testing")
        assert category.slug == "testing"
