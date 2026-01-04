import pytest

from simplecasts.models import (
    Recommendation,
)
from simplecasts.tests.factories import (
    RecommendationFactory,
)


class TestRecommendationManager:
    @pytest.mark.django_db
    def test_bulk_delete(self):
        RecommendationFactory.create_batch(3)
        Recommendation.objects.bulk_delete()
        assert Recommendation.objects.count() == 0
