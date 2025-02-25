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

    @pytest.mark.parametrize(
        ("file_size", "duration", "media_type", "expected"),
        [
            pytest.param(None, None, "audio/ogg", 0, id="both none"),
            pytest.param(0, 0, "audio/ogg", 0, id="both zero"),
            pytest.param(
                1,  # Erroneous file size (1 byte, but should be treated as 1 MB)
                None,
                "audio/mp3",
                0,  # File size is capped to 1024 bytes (1 KB)
                id="erroneous-1-byte-file-size",
            ),
            pytest.param(
                5000000,
                None,
                "audio/mp4",
                5000000,  # File size is provided, no calculation needed
                id="only file size given",
            ),
            pytest.param(
                None,
                "0:02:00",
                "audio/ogg",
                1440000,  # Calculated expected file size (bytes) for 2 minutes of audio at 64 kbps
                id="file size is None",
            ),
            pytest.param(
                1,
                "0:02:00",
                "audio/ogg",
                1440000,  # Calculated expected file size (bytes) for 2 minutes of audio at 64 kbps
                id="file size is < 1MB",
            ),
            pytest.param(
                2048576,
                "0:02:00",
                "audio/ogg",
                2048576,  # Calculated expected file size (bytes) for 2 minutes of audio at 64 kbps
                id="file size given",
            ),
            pytest.param(
                0,
                "0:02:00",
                "audio/ogg",
                1440000,  # Calculated expected file size (bytes) for 2 minutes of audio at 96 kbps
                id="ogg-2min-default",
            ),
            pytest.param(
                0,
                "0:05:00",
                "audio/mp4",
                4800000,  # Calculated expected file size (bytes) for 5 minutes of audio at 128 kbps
                id="mp4-5min-default",
            ),
            pytest.param(
                0,
                "0:30:00",
                "audio/mp3",
                28800000,  # Calculated expected file size (bytes) for 30 minutes of audio at 128 kbps
                id="mp3-30min-default",
            ),
            pytest.param(
                0,
                "1:12:34",
                "audio/mp3",
                69664000,  # Calculated expected file size (bytes) for 1 hour 12 minutes 34 seconds at 128 kbps
                id="mp3-1hr12min34sec",
            ),
            pytest.param(
                0,
                "0:10:00",
                "audio/unknown",
                9600000,  # Calculated expected file size (bytes) for 10 minutes of audio at 128 kbps
                id="unknown-mime-default",
            ),
        ],
    )
    def test_estimated_file_size(self, file_size, duration, media_type, expected):
        episode = Episode(
            file_size=file_size,
            duration=duration,
            media_type=media_type,
        )
        assert episode.estimated_file_size == expected

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
        ("episode_type", "is_bonus", "is_trailer", "is_full"),
        [
            pytest.param(Episode.EpisodeType.BONUS, True, False, False, id="bonus"),
            pytest.param(Episode.EpisodeType.TRAILER, False, True, False, id="trailer"),
            pytest.param(Episode.EpisodeType.FULL, False, False, True, id="full"),
        ],
    )
    def test_episode_types(self, episode_type, is_bonus, is_trailer, is_full):
        episode = Episode(episode_type=episode_type)
        assert episode.is_full_episode() is is_full
        assert episode.is_bonus_episode() is is_bonus
        assert episode.is_trailer() is is_trailer

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
        )
        assert str(audio_log) == "user 1 | episode 2"

    @pytest.mark.parametrize(
        ("current_time", "duration", "expected"),
        [
            pytest.param(0, None, 0, id="both zero"),
            pytest.param(0, "1:0:0", 0, id="current time zero"),
            pytest.param(60 * 60, None, 0, id="duration zero"),
            pytest.param(60 * 60, "1:0:0", 100, id="both one hour"),
            pytest.param(60 * 30, "1:0:0", 50, id="current time half"),
            pytest.param(60 * 60, "0:30:0", 100, id="more than 100 percent"),
        ],
    )
    def test_percent_complete(self, current_time, duration, expected):
        audio_log = AudioLog(
            current_time=current_time,
            episode=Episode(duration=duration),
        )
        assert audio_log.percent_complete == expected
