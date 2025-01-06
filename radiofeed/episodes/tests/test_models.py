import datetime

import pytest

from radiofeed.episodes.models import AudioLog, Bookmark, Episode
from radiofeed.episodes.tests.factories import (
    AudioLogFactory,
    BookmarkFactory,
    EpisodeFactory,
)
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import PodcastFactory, SubscriptionFactory


class TestEpisodeManager:
    @pytest.mark.django_db
    def test_search(self):
        EpisodeFactory(title="testing")
        assert Episode.objects.search("testing").count() == 1

    @pytest.mark.django_db
    def test_search_empty(self):
        EpisodeFactory(title="testing")
        assert Episode.objects.search("").count() == 0

    @pytest.mark.django_db
    def test_subscribed_true(self, user, episode):
        SubscriptionFactory(subscriber=user, podcast=episode.podcast)
        assert Episode.objects.subscribed(user).exists() is True

    @pytest.mark.django_db
    def test_subscribed_false(self, user, episode):
        assert Episode.objects.subscribed(user).exists() is False


class TestEpisodeModel:
    link = "https://example.com"

    @pytest.mark.django_db
    def test_next_episode_if_none(self, episode):
        assert episode.get_next_episode() is None

    @pytest.mark.django_db
    def test_previous_episode_if_none(self, episode):
        assert episode.get_previous_episode() is None

    @pytest.mark.django_db
    def test_next_episode_not_same_podcast(self, episode):
        EpisodeFactory(
            pub_date=episode.pub_date + datetime.timedelta(days=2),
        )

        assert episode.get_next_episode() is None

    @pytest.mark.django_db
    def test_previous_episode_not_same_podcast(self, episode):
        EpisodeFactory(
            pub_date=episode.pub_date - datetime.timedelta(days=2),
        )

        assert episode.get_previous_episode() is None

    @pytest.mark.django_db
    def test_next_episode(self, episode):
        next_episode = EpisodeFactory(
            podcast=episode.podcast,
            pub_date=episode.pub_date + datetime.timedelta(days=2),
        )

        assert episode.get_next_episode() == next_episode

    @pytest.mark.django_db
    def test_previous_episode(self, episode):
        previous_episode = EpisodeFactory(
            podcast=episode.podcast,
            pub_date=episode.pub_date - datetime.timedelta(days=2),
        )

        assert episode.get_previous_episode() == previous_episode

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
        assert Episode().slug == "no-title"

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

    def test_get_file_size(self):
        assert Episode(length=500).get_file_size() == "500\xa0bytes"

    def test_get_file_size_if_none(self):
        assert Episode(length=None).get_file_size() is None

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
        ("episode_type", "expected"),
        [
            pytest.param(None, None, id="none"),
            pytest.param("full", None, id="full lowercase"),
            pytest.param("FULL", None, id="full uppercase"),
            pytest.param("trailer", "trailer", id="trailer"),
        ],
    )
    def test_get_episode_type(self, episode_type, expected):
        return Episode(episode_type=episode_type) == expected

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


class TestBookmarkManager:
    @pytest.mark.django_db
    def test_search(self):
        episode = EpisodeFactory(title="testing")
        BookmarkFactory(episode=episode)
        assert Bookmark.objects.search("testing").count() == 1


class TestBookmarkModel:
    def test_str(self):
        assert str(Bookmark(episode_id=1, user_id=1)) == "user 1 | episode 1"


class TestAudioLogManager:
    @pytest.mark.django_db
    def test_search(self):
        episode = EpisodeFactory(title="testing")
        AudioLogFactory(episode=episode)
        assert AudioLog.objects.search("testing").count() == 1


class TestAudioLogModel:
    def test_str(self):
        audio_log = AudioLog(
            episode_id=2,
            user_id=1,
            listened=datetime.datetime(year=2024, month=9, day=10),
        )
        assert str(audio_log) == "user 1 | episode 2 | 2024-09-10T00:00:00"
