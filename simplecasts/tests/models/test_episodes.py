from datetime import timedelta

import pytest

from simplecasts.models import Episode, Podcast
from simplecasts.tests.factories import EpisodeFactory, PodcastFactory


class TestEpisodeManager:
    @pytest.mark.django_db
    def test_search(self):
        episode = EpisodeFactory(title="UniqueTitle123")
        results = Episode.objects.search("UniqueTitle123")
        assert episode in results

    @pytest.mark.django_db
    def test_search_no_results(self):
        EpisodeFactory(title="Some Other Title")
        results = Episode.objects.search("NonExistentTitle456")
        assert results.count() == 0

    @pytest.mark.django_db
    def test_search_empty_query(self):
        EpisodeFactory(title="Any Title")
        results = Episode.objects.search("")
        assert results.count() == 0


class TestEpisodeModel:
    link = "https://example.com"

    @pytest.mark.django_db
    def test_next_episode_if_none(self, episode):
        assert episode.next_episode is None

    @pytest.mark.django_db
    def test_previous_episode_if_none(self, episode):
        assert episode.previous_episode is None

    @pytest.mark.django_db
    def test_next_episode_not_same_podcast(self, episode):
        EpisodeFactory(
            pub_date=episode.pub_date + timedelta(days=2),
        )

        assert episode.next_episode is None

    @pytest.mark.django_db
    def test_previous_episode_not_same_podcast(self, episode):
        EpisodeFactory(
            pub_date=episode.pub_date - timedelta(days=2),
        )

        assert episode.previous_episode is None

    @pytest.mark.django_db
    def test_next_episode(self, episode):
        next_episode = EpisodeFactory(
            podcast=episode.podcast,
            pub_date=episode.pub_date + timedelta(days=2),
        )

        assert episode.next_episode == next_episode

    @pytest.mark.django_db
    def test_previous_episode(self, episode):
        previous_episode = EpisodeFactory(
            podcast=episode.podcast,
            pub_date=episode.pub_date - timedelta(days=2),
        )

        assert episode.previous_episode == previous_episode

    def test_episode_explicit(self):
        assert Episode(explicit=True).is_explicit() is True

    def test_podcast_explicit(self):
        assert (
            Episode(explicit=False, podcast=Podcast(explicit=True)).is_explicit()
            is True
        )

    def test_not_explicit(self):
        assert (
            Episode(explicit=False, podcast=Podcast(explicit=False)).is_explicit()
            is False
        )

    def test_slug(self):
        episode = Episode(title="Testing")
        assert episode.slug == "testing"

    def test_slug_if_title_empty(self):
        assert Episode().slug == "episode"

    def test_str(self):
        assert str(Episode(title="testing")) == "testing"

    def test_str_no_title(self):
        episode = Episode(title="", guid="abc123")
        assert str(episode) == episode.guid

    def test_cleaned_title(self):
        episode = Episode(title="<b>Test &amp; Code")
        assert episode.cleaned_title == "Test & Code"

    def test_cleaned_description(self):
        episode = Episode(description="<b>Test &amp; Code")
        assert episode.cleaned_description == "Test & Code"

    @pytest.mark.django_db
    def test_get_cover_url_if_episode_cover(self, podcast):
        episode = EpisodeFactory(
            podcast=podcast, cover_url="https://example.com/episode-cover.jpg"
        )
        assert episode.get_cover_url() == "https://example.com/episode-cover.jpg"

    @pytest.mark.django_db
    def test_get_cover_url_if_podcast_cover(self, episode):
        assert episode.get_cover_url() == "https://example.com/cover.jpg"

    @pytest.mark.django_db
    def test_get_cover_url_if_none(self):
        episode = EpisodeFactory(podcast=PodcastFactory(cover_url=""))
        assert episode.get_cover_url() == ""

    @pytest.mark.parametrize(
        ("duration", "expected"),
        [
            pytest.param("2:30:40", 9040, id="hours"),
            pytest.param("2:30:40:2903903", 9040, id="extra digit"),
            pytest.param("30:40", 1840, id="minutes and seconds"),
            pytest.param("40", 40, id="seconds"),
            pytest.param("NaN", 0, id="non-numeric"),
            pytest.param("", 0, id="empty"),
        ],
    )
    def test_duration_in_seconds(self, duration, expected):
        assert Episode(duration=duration).duration_in_seconds == expected
