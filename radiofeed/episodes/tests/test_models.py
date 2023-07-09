import datetime

import pytest

from radiofeed.episodes.models import AudioLog, Bookmark, Episode
from radiofeed.episodes.tests.factories import (
    create_audio_log,
    create_bookmark,
    create_episode,
)
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import create_podcast


class TestEpisodeManager:
    @pytest.mark.django_db()
    def test_search(self):
        create_episode(title="testing")
        assert Episode.objects.search("testing").count() == 1

    @pytest.mark.django_db()
    def test_search_empty(self):
        create_episode(title="testing")
        assert Episode.objects.search("").count() == 0


class TestEpisodeModel:
    link = "https://example.com"

    @pytest.mark.django_db()
    def test_get_next_episode_if_none(self, episode):
        assert episode.get_next_episode() is None

    @pytest.mark.django_db()
    def test_get_previous_episode_if_none(self, episode):
        assert episode.get_previous_episode() is None

    @pytest.mark.django_db()
    def test_get_next_episode_not_same_podcast(self, episode):
        create_episode(
            pub_date=episode.pub_date + datetime.timedelta(days=2),
        )

        assert episode.get_next_episode() is None

    @pytest.mark.django_db()
    def test_get_previous_episode_not_same_podcast(self, episode):
        create_episode(
            pub_date=episode.pub_date - datetime.timedelta(days=2),
        )

        assert episode.get_previous_episode() is None

    @pytest.mark.django_db()
    def test_get_next_episode(self, episode):
        next_episode = create_episode(
            podcast=episode.podcast,
            pub_date=episode.pub_date + datetime.timedelta(days=2),
        )

        assert episode.get_next_episode() == next_episode

    @pytest.mark.django_db()
    def test_get_previous_episode(self, episode):
        previous_episode = create_episode(
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

    def test_duration_in_seconds_hours_minutes_seconds(self):
        assert Episode(duration="2:30:40").duration_in_seconds == 9040

    def test_duration_in_seconds_hours_minutes_seconds_extra_digit(self):
        assert Episode(duration="2:30:40:2903903").duration_in_seconds == 9040

    def test_duration_in_seconds_minutes_seconds(self):
        assert Episode(duration="30:40").duration_in_seconds == 1840

    def test_duration_in_seconds_seconds_only(self):
        assert Episode(duration="40").duration_in_seconds == 40

    def test_get_duration_in_seconds_if_empty(self):
        assert Episode(duration="").duration_in_seconds == 0

    def test_duration_in_seconds_if_non_numeric(self):
        assert Episode(duration="NaN").duration_in_seconds == 0

    def test_duration_in_seconds_if_seconds_only(self):
        assert Episode(duration="60").duration_in_seconds == 60

    def test_duration_in_seconds_if_minutes_and_seconds(self):
        assert Episode(duration="2:30").duration_in_seconds == 150

    def test_duration_in_seconds_if_hours_minutes_and_seconds(self):
        assert Episode(duration="2:30:30").duration_in_seconds == 9030

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

    @pytest.mark.django_db()
    def test_get_media_metadata(self):
        cover_url = "https://www.omnycontent.com/d/playlist/aaea4e69-af51-495e-afc9-a9760146922b/9b63d479-4382-4198-8e63-aac7013964ff/e5ebd302-9d49-4c56-a234-aac701396502/image.jpg?t=1568401263\u0026size=Large"
        episode = create_episode(podcast=create_podcast(cover_url=cover_url))
        data = episode.get_media_metadata()
        assert data["title"] == episode.title
        assert data["album"] == episode.podcast.title
        assert data["artist"] == episode.podcast.owner
        assert data["artwork"][0] == {
            "src": cover_url,
            "sizes": "96x96",
            "type": "image/jpeg",
        }

    @pytest.mark.django_db()
    def test_get_cover_url_if_episode_cover(self, podcast):
        episode = create_episode(
            podcast=podcast, cover_url="https://example.com/episode-cover.jpg"
        )
        assert episode.get_cover_url() == "https://example.com/episode-cover.jpg"

    @pytest.mark.django_db()
    def test_get_cover_url_if_podcast_cover(self, episode):
        assert episode.get_cover_url() == "https://example.com/cover.jpg"

    @pytest.mark.django_db()
    def test_get_cover_url_if_none(self):
        episode = create_episode(podcast=create_podcast(cover_url=None))
        assert episode.get_cover_url() is None

    @pytest.mark.parametrize(
        ("episode_type", "number", "season", "expected"),
        [
            ("full", None, None, {}),
            ("trailer", None, None, {"type": "trailer"}),
            ("trailer", 10, 3, {"type": "trailer", "episode": 10, "season": 3}),
            ("full", 10, 3, {"episode": 10, "season": 3}),
            ("full", 10, None, {"episode": 10}),
            ("full", None, 3, {"season": 3}),
        ],
    )
    def test_get_episode_metadata(self, episode_type, number, season, expected):
        assert (
            Episode(
                episode_type=episode_type,
                episode=number,
                season=season,
            ).get_episode_metadata()
            == expected
        )


class TestBookmarkManager:
    @pytest.mark.django_db()
    def test_search(self):
        episode = create_episode(title="testing")
        create_bookmark(episode=episode)
        assert Bookmark.objects.search("testing").count() == 1


class TestAudioLogManager:
    @pytest.mark.django_db()
    def test_search(self):
        episode = create_episode(title="testing")
        create_audio_log(episode=episode)
        assert AudioLog.objects.search("testing").count() == 1
