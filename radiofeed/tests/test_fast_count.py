import pytest

from radiofeed.fast_count import FastCountPaginator
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import PodcastFactory


class TestFastCountPaginator:
    @pytest.mark.django_db
    def test_with_fast_count(self):
        PodcastFactory.create_batch(30)
        paginator = FastCountPaginator(Podcast.objects.all(), 10)
        assert paginator.count == 30


class TestFastCountQuerySetMixin:
    reltuple_count = "radiofeed.fast_count.get_reltuple_count"

    @pytest.mark.django_db
    def test_fast_count_if_gt_1000(self, mocker):
        mocker.patch(self.reltuple_count, return_value=2000)
        assert Podcast.objects.fast_count() == 2000

    @pytest.mark.django_db
    def test_fast_count_if_lt_1000(self, mocker, podcast):
        mocker.patch(self.reltuple_count, return_value=100)
        assert Podcast.objects.fast_count() == 1

    @pytest.mark.django_db
    def test_fast_count_if_filter(self, mocker):
        mocker.patch(self.reltuple_count, return_value=2000)
        PodcastFactory(title="test")
        assert Podcast.objects.filter(title="test").fast_count() == 1
