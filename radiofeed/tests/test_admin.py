import pytest

from radiofeed.admin import FastCountPaginator, count_reltuples
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import PodcastFactory


class TestCountReltuples:
    @pytest.mark.django_db
    def test_returns_count_for_existing_table(self):
        result = count_reltuples(Podcast._meta.db_table)
        assert isinstance(result, int)
        assert result >= 0

    def test_returns_zero_when_fetchone_is_none(self, mocker):
        mock_cursor = mocker.MagicMock()
        mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = mocker.MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = None
        mocker.patch("radiofeed.admin.connection.cursor", return_value=mock_cursor)
        assert count_reltuples("nonexistent_table") == 0


class TestFastCountPaginator:
    @pytest.mark.django_db
    def test_unfiltered_queryset_uses_reltuples(self, mocker):
        mocker.patch(
            "radiofeed.admin.count_reltuples",
            return_value=100,
        )
        paginator = FastCountPaginator(Podcast.objects.all(), 25)
        assert paginator.count == 100

    @pytest.mark.django_db
    def test_filtered_queryset_uses_standard_count(self):
        PodcastFactory.create_batch(3, active=True)
        PodcastFactory.create_batch(2, active=False)
        paginator = FastCountPaginator(Podcast.objects.filter(active=True), 25)
        assert paginator.count == 3

    def test_list_uses_len(self):
        paginator = FastCountPaginator([1, 2, 3], 25)
        assert paginator.count == 3

    @pytest.mark.django_db
    def test_reltuples_zero_falls_back_to_standard_count(self, mocker):
        mocker.patch(
            "radiofeed.admin.count_reltuples",
            return_value=0,
        )
        PodcastFactory.create_batch(3)
        paginator = FastCountPaginator(Podcast.objects.all(), 25)
        assert paginator.count == 3
