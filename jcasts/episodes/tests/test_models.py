import datetime

import pytest

from django.contrib.sites.models import Site
from django.db import IntegrityError, transaction
from django.utils import timezone

from jcasts.episodes.factories import (
    AudioLogFactory,
    EpisodeFactory,
    FavoriteFactory,
    QueueItemFactory,
)
from jcasts.episodes.models import AudioLog, Episode, Favorite, QueueItem
from jcasts.podcasts.factories import FollowFactory
from jcasts.podcasts.models import Podcast


class TestEpisodeManager:
    def test_get_next_episode_if_none(self, episode):

        assert Episode.objects.get_next_episode(episode) is None

    def test_get_previous_episode_if_none(self, episode):

        assert Episode.objects.get_previous_episode(episode) is None

    def test_get_next_episode(self, episode):

        next_episode = EpisodeFactory(
            podcast=episode.podcast,
            pub_date=episode.pub_date + datetime.timedelta(days=2),
        )

        assert Episode.objects.get_next_episode(episode) == next_episode

    def test_get_next_episode_not_same_podcast(self, episode):

        EpisodeFactory(
            pub_date=episode.pub_date + datetime.timedelta(days=2),
        )

        assert Episode.objects.get_next_episode(episode) is None

    def test_get_next_episode_before_current(self, episode):

        EpisodeFactory(
            podcast=episode.podcast,
            pub_date=episode.pub_date - datetime.timedelta(days=2),
        )

        assert Episode.objects.get_next_episode(episode) is None

    def test_get_previous_episode(self, episode):

        previous_episode = EpisodeFactory(
            podcast=episode.podcast,
            pub_date=episode.pub_date - datetime.timedelta(days=2),
        )

        assert Episode.objects.get_previous_episode(episode) == previous_episode

    def test_get_previous_not_same_podcast(self, episode):

        EpisodeFactory(
            pub_date=episode.pub_date + datetime.timedelta(days=2),
        )

        assert Episode.objects.get_previous_episode(episode) is None

    def test_get_previous_episode_after_current(self, episode):

        EpisodeFactory(
            podcast=episode.podcast,
            pub_date=episode.pub_date + datetime.timedelta(days=2),
        )

        assert Episode.objects.get_previous_episode(episode) is None

    def test_recommended_no_follows(self, db, user):

        assert Episode.objects.recommended(user).count() == 0

    def test_recommended(self, db, user):

        podcast = FollowFactory(user=user).podcast
        # ok
        first = EpisodeFactory(podcast=podcast)

        # not following
        EpisodeFactory()

        # listened
        AudioLogFactory(episode__podcast=podcast, user=user)

        # favorite
        FavoriteFactory(episode__podcast=podcast, user=user)

        # queued
        QueueItemFactory(episode__podcast=podcast, user=user)

        # trailer
        EpisodeFactory(podcast=podcast, episode_type="trailer")

        # too old
        EpisodeFactory(
            podcast=podcast, pub_date=timezone.now() - datetime.timedelta(days=30)
        )

        episodes = Episode.objects.recommended(user)
        assert episodes.count() == 1
        assert episodes.first() == first

    def test_with_current_time_if_anonymous(self, db, anonymous_user):
        EpisodeFactory()
        episode = Episode.objects.with_current_time(anonymous_user).first()

        assert episode.current_time == 0
        assert not episode.completed
        assert not episode.listened

    def test_with_current_time_if_not_played(self, user):
        EpisodeFactory()
        episode = Episode.objects.with_current_time(user).first()

        assert not episode.current_time
        assert not episode.completed
        assert not episode.listened

    def test_with_current_time_if_played(self, user):
        log = AudioLogFactory(user=user, current_time=20, updated=timezone.now())
        episode = Episode.objects.with_current_time(user).first()

        assert episode.current_time == 20
        assert not episode.completed
        assert episode.listened == log.updated

    def test_with_current_time_if_completed(self, user):
        log = AudioLogFactory(
            user=user,
            current_time=20,
            completed=timezone.now(),
            updated=timezone.now(),
        )
        episode = Episode.objects.with_current_time(user).first()

        assert episode.current_time == 20
        assert episode.completed
        assert episode.listened == log.updated

    def test_search(self, db):
        EpisodeFactory(title="testing")
        assert Episode.objects.search("testing").count() == 1


class TestEpisodeModel:
    link = "https://example.com"

    def test_get_link_if_episode(self):
        assert Episode(link=self.link).get_link() == self.link

    def test_get_link_if_podcast(self):

        assert (
            Episode(link=None, podcast=Podcast(link=self.link)).get_link() == self.link
        )

    def test_get_link_if_none(self):

        assert Episode(link=None, podcast=Podcast(link=None)).get_link() is None

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

    def test_get_media_url_ext(self):

        assert (
            Episode(
                media_url="https://thegrognardfiles.com/wp-content/uploads/2021/08/Episode-50-Part-1-Fighting-Fantasy-with-Ian-Livingstone-27_08_2021-23.58.mp3"
            ).get_media_url_ext()
            == "mp3"
        )

    def test_time_remaining(self):
        episode = Episode(duration="1:00:00")
        episode.current_time = 1200
        assert episode.time_remaining == 2400

    def test_time_remaining_if_no_duration(self):
        episode = Episode(duration="")
        episode.current_time = 1200
        assert episode.time_remaining == 0

    def test_time_remaining_current_time_none(self):
        episode = Episode(duration="1:00:00")
        episode.current_time = None
        assert episode.time_remaining == 3600

    def test_time_remaining_current_time_not_set(self):
        episode = Episode(duration="1:00:00")
        with pytest.raises(AssertionError):
            episode.time_remaining

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

    def test_is_completed_if_not_set(self, episode):
        with pytest.raises(AssertionError):
            episode.is_completed

    def test_is_completed_if_marked_complete(self, user, episode):
        AudioLogFactory(
            user=user,
            current_time=50,
            updated=timezone.now(),
            completed=timezone.now(),
            episode=episode,
        )
        assert Episode.objects.with_current_time(user).first().is_completed

    def test_pc_complete_if_duration_none(self, user):
        episode = EpisodeFactory(duration="")

        AudioLogFactory(
            user=user,
            current_time=50,
            updated=timezone.now(),
            episode=episode,
        )
        assert not Episode.objects.with_current_time(user).first().is_completed

    def test_is_completed_if_pc_complete_under_100(self, user, episode):
        AudioLogFactory(
            user=user,
            current_time=50,
            updated=timezone.now(),
            episode=episode,
        )
        assert not Episode.objects.with_current_time(user).first().is_completed

    def test_is_completed_if_pc_complete_over_100(self, user, episode):
        AudioLogFactory(
            user=user,
            current_time=100,
            updated=timezone.now(),
            episode=episode,
        )
        assert Episode.objects.with_current_time(user).first().is_completed

    def test_pc_complete_without_current_time_attr(self, user, episode):
        AudioLogFactory(
            user=user,
            current_time=50,
            updated=timezone.now(),
            episode=episode,
        )
        with pytest.raises(AssertionError):
            Episode.objects.first().pc_complete

    def test_pc_complete(self, user, episode):
        AudioLogFactory(
            user=user,
            current_time=50,
            updated=timezone.now(),
            episode=episode,
        )
        assert Episode.objects.with_current_time(user).first().pc_complete == 50

    def test_pc_complete_zero_current_time(self, user, episode):
        AudioLogFactory(
            user=user,
            current_time=0,
            updated=timezone.now(),
            episode=episode,
        )
        assert Episode.objects.with_current_time(user).first().pc_complete == 0

    def test_pc_complete_zero_duration(self, user, episode):
        AudioLogFactory(
            user=user,
            current_time=0,
            updated=timezone.now(),
            episode=EpisodeFactory(duration=""),
        )
        assert Episode.objects.with_current_time(user).first().pc_complete == 0

    def test_pc_complete_gt_100(self, user, episode):
        AudioLogFactory(
            user=user,
            current_time=120,
            updated=timezone.now(),
            episode=episode,
        )
        assert Episode.objects.with_current_time(user).first().pc_complete == 100

    def test_pc_complete_marked_complete(self, user, episode):
        now = timezone.now()
        AudioLogFactory(
            user=user,
            current_time=50,
            updated=now,
            completed=now,
            episode=episode,
        )
        assert Episode.objects.with_current_time(user).first().pc_complete == 100

    def test_pc_complete_not_played(self, user, episode):
        assert Episode.objects.with_current_time(user).first().pc_complete == 0

    def test_pc_complete_anonymous(self, anonymous_user, episode):
        AudioLogFactory(
            current_time=50,
            updated=timezone.now(),
            episode=episode,
        )
        assert (
            Episode.objects.with_current_time(anonymous_user).first().pc_complete == 0
        )

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

    def test_get_media_metadata(self, db):
        cover_url = "https://www.omnycontent.com/d/playlist/aaea4e69-af51-495e-afc9-a9760146922b/9b63d479-4382-4198-8e63-aac7013964ff/e5ebd302-9d49-4c56-a234-aac701396502/image.jpg?t=1568401263\u0026size=Large"
        episode = EpisodeFactory(podcast__cover_url=cover_url)
        data = episode.get_media_metadata()
        assert data["title"] == episode.title
        assert data["album"] == episode.podcast.title
        assert data["artist"] == episode.podcast.owner
        assert data["artwork"][0] == {
            "src": cover_url,
            "sizes": "96x96",
            "type": "image/jpeg",
        }

    def test_get_cover_url_if_episode_cover(self, podcast):
        episode = EpisodeFactory(
            podcast=podcast, cover_url="https://example.com/episode-cover.jpg"
        )
        assert episode.get_cover_url() == "https://example.com/episode-cover.jpg"

    def test_get_cover_url_if_podcast_cover(self, episode):
        assert episode.get_cover_url() == "https://example.com/cover.jpg"

    def test_get_cover_url_if_none(self, db):
        episode = EpisodeFactory(podcast__cover_url=None)
        assert episode.get_cover_url() is None

    def test_get_opengraph_data(self, rf, episode):
        req = rf.get("/")
        req.site = Site.objects.get_current()
        data = episode.get_opengraph_data(req)
        assert episode.title in data["title"]
        assert data["url"] == "http://testserver" + episode.get_absolute_url()

    def test_is_favorited_anonymous(self, anonymous_user, episode):
        assert not episode.is_favorited(anonymous_user)

    def test_is_favorited_false(self, user, episode):
        assert not episode.is_favorited(user)

    def test_is_favorited_true(self, user, episode):
        fave = FavoriteFactory(user=user, episode=episode)
        assert fave.episode.is_favorited(fave.user)

    def test_is_queued_anonymous(self, anonymous_user, episode):
        assert not episode.is_queued(anonymous_user)

    def test_is_queued_false(self, user, episode):
        assert not episode.is_queued(user)

    def test_is_queued_true(self, user, episode):
        item = QueueItemFactory(user=user, episode=episode)
        assert item.episode.is_queued(item.user)

    @pytest.mark.parametrize(
        "episode_type,number,season,expected",
        [
            ("full", None, None, ""),
            ("trailer", None, None, "Trailer"),
            ("trailer", 10, 3, "Trailer"),
            ("full", 10, 3, "Episode 10 Season 3"),
            ("full", 10, None, "Episode 10"),
            ("full", None, 3, "Season 3"),
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


class TestFavoriteManager:
    def test_search(self, db):
        episode = EpisodeFactory(title="testing")
        FavoriteFactory(episode=episode)
        assert Favorite.objects.search("testing").count() == 1


class TestAudioLogManager:
    def test_search(self, db):
        episode = EpisodeFactory(title="testing")
        AudioLogFactory(episode=episode)
        assert AudioLog.objects.search("testing").count() == 1


class TestAudioLogModel:
    def test_to_json(self, db):
        log = AudioLogFactory()
        data = log.to_json()
        assert data["episode"]["id"] == log.episode.id
        assert data["episode"]["url"] == log.episode.get_absolute_url()
        assert data["podcast"]["title"] == log.episode.podcast.title
        assert data["podcast"]["url"] == log.episode.podcast.get_absolute_url()


class TestQueueItemManager:
    def test_move_items(self, user):
        first = QueueItemFactory(user=user)
        second = QueueItemFactory(user=user)
        third = QueueItemFactory(user=user)

        items = QueueItem.objects.filter(user=user).order_by("position")

        assert items[0] == first
        assert items[1] == second
        assert items[2] == third

        QueueItem.objects.move_items(user, [third.id, first.id, second.id])

        items = QueueItem.objects.filter(user=user).order_by("position")

        assert items[0] == third
        assert items[1] == first
        assert items[2] == second

    def test_create_item_start_empty(self, user, episode):
        item = self.create_item(user, episode)

        assert item.episode == episode
        assert item.user == user
        assert item.position == 1

    def test_create_item_start_with_other_items(self, user, episode):
        other = QueueItemFactory(user=user, position=1)

        item = self.create_item(user, episode)

        assert item.episode == episode
        assert item.user == user
        assert item.position == 2

        other.refresh_from_db()
        assert other.position == 1

    @pytest.mark.django_db(transaction=True)
    def test_create_item_start_already_exists(self, user):
        other = QueueItemFactory(user=user, position=1)

        with transaction.atomic():
            with pytest.raises(IntegrityError):
                QueueItem.objects.create_item(
                    user,
                    other.episode,
                    add_to_start=True,
                )
        assert QueueItem.objects.count() == 1

        other.refresh_from_db()
        assert other.position == 1

    def test_create_item_end_empty(self, user, episode):
        item = self.create_item(user, episode)

        assert item.episode == episode
        assert item.user == user
        assert item.position == 1

    def test_create_item_end_with_other_items(self, user, episode):
        other = QueueItemFactory(user=user, position=1)

        item = self.create_item(user, episode)

        assert item.episode == episode
        assert item.user == user
        assert item.position == 2

        other.refresh_from_db()
        assert other.position == 1

    @pytest.mark.django_db(transaction=True)
    def test_create_item_end_already_exists(self, user):
        other = QueueItemFactory(user=user, position=1)

        with transaction.atomic():
            with pytest.raises(IntegrityError):
                QueueItem.objects.create_item(
                    user,
                    other.episode,
                    add_to_start=False,
                )
        assert QueueItem.objects.count() == 1

        other.refresh_from_db()
        assert other.position == 1

    def create_item(self, user, episode, add_to_start=False):
        return QueueItem.objects.create_item(user, episode, add_to_start)
