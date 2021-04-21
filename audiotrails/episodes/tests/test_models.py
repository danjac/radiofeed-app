import datetime

import pytest

from django.utils import timezone

from ..factories import (
    AudioLogFactory,
    EpisodeFactory,
    FavoriteFactory,
    QueueItemFactory,
)
from ..models import AudioLog, Episode, Favorite, QueueItem

pytestmark = pytest.mark.django_db


class TestEpisodeManager:
    def test_with_current_time_if_anonymous(self, anonymous_user):
        EpisodeFactory()
        episode = Episode.objects.with_current_time(anonymous_user).first()
        assert episode.current_time == 0
        assert episode.completed is False
        assert episode.listened is None

    def test_with_current_time_if_not_played(self, user):
        EpisodeFactory()
        episode = Episode.objects.with_current_time(user).first()
        assert episode.current_time is None
        assert episode.completed is None
        assert episode.listened is None

    def test_with_current_time_if_played(self, user):
        log = AudioLogFactory(user=user, current_time=20, updated=timezone.now())
        episode = Episode.objects.with_current_time(user).first()
        assert episode.current_time == 20
        assert episode.completed is None
        assert episode.listened == log.updated

    def test_with_current_time_if_completed(self, user):
        log = AudioLogFactory(
            user=user, current_time=20, completed=timezone.now(), updated=timezone.now()
        )
        episode = Episode.objects.with_current_time(user).first()
        assert episode.current_time == 20
        assert episode.completed is not None
        assert episode.listened == log.updated

    def test_search(self):
        EpisodeFactory(title="testing")
        assert Episode.objects.search("testing").count() == 1


class TestEpisodeModel:
    def test_duration_in_seconds_if_empty_or_none(self):
        assert Episode(duration=None).get_duration_in_seconds() == 0
        assert Episode(duration="").get_duration_in_seconds() == 0

    def test_duration_in_seconds_invalid_string(self):
        assert Episode(duration="oops").get_duration_in_seconds() == 0

    def test_duration_in_seconds_hours_minutes_seconds(self):
        assert Episode(duration="2:30:40").get_duration_in_seconds() == 9040

    def test_duration_in_seconds_hours_minutes_seconds_extra_digit(self):
        assert Episode(duration="2:30:40:2903903").get_duration_in_seconds() == 9040

    def test_duration_in_seconds_minutes_seconds(self):
        assert Episode(duration="30:40").get_duration_in_seconds() == 1840

    def test_duration_in_seconds_seconds_only(self):
        assert Episode(duration="40").get_duration_in_seconds() == 40

    def test_get_media_metadata(self, episode):
        data = episode.get_media_metadata()
        assert data["title"] == episode.title
        assert data["album"] == episode.podcast.title
        assert data["artist"] == episode.podcast.creators

    def test_slug(self):
        episode = Episode(title="Testing")
        assert episode.slug == "testing"

    def test_slug_if_title_empty(self):
        assert Episode().slug == "episode"

    def test_get_duration_in_seconds_if_empty(self):
        assert Episode().get_duration_in_seconds() == 0
        assert Episode(duration="").get_duration_in_seconds() == 0

    def test_duration_in_seconds_if_non_numeric(self):
        assert Episode(duration="NaN").get_duration_in_seconds() == 0

    def test_duration_in_seconds_if_seconds_only(self):
        assert Episode(duration="60").get_duration_in_seconds() == 60

    def test_duration_in_seconds_if_minutes_and_seconds(self):
        assert Episode(duration="2:30").get_duration_in_seconds() == 150

    def test_duration_in_seconds_if_hours_minutes_and_seconds(self):
        assert Episode(duration="2:30:30").get_duration_in_seconds() == 9030

    def test_has_next_previous_episode(self, episode):
        assert episode.get_next_episode() is None
        assert episode.get_previous_episode() is None

        next_episode = EpisodeFactory(
            podcast=episode.podcast,
            pub_date=episode.pub_date + datetime.timedelta(days=2),
        )

        previous_episode = EpisodeFactory(
            podcast=episode.podcast,
            pub_date=episode.pub_date - datetime.timedelta(days=2),
        )

        EpisodeFactory(
            podcast=episode.podcast,
            pub_date=episode.pub_date - datetime.timedelta(days=3),
        )

        assert episode.get_next_episode() == next_episode
        assert episode.get_previous_episode() == previous_episode

    def test_get_pc_complete_without_current_time_attr(self, user):
        episode = EpisodeFactory(duration="100")
        AudioLogFactory(
            user=user, current_time=50, updated=timezone.now(), episode=episode
        )
        assert Episode.objects.first().get_pc_completed() == 0

    def test_get_pc_complete(self, user):
        episode = EpisodeFactory(duration="100")
        AudioLogFactory(
            user=user, current_time=50, updated=timezone.now(), episode=episode
        )
        assert Episode.objects.with_current_time(user).first().get_pc_completed() == 50

    def test_get_pc_complete_zero_current_time(self, user):
        episode = EpisodeFactory(duration="100")
        AudioLogFactory(
            user=user, current_time=0, updated=timezone.now(), episode=episode
        )
        assert Episode.objects.with_current_time(user).first().get_pc_completed() == 0

    def test_get_pc_complete_zero_duration(self, user):
        episode = EpisodeFactory(duration="")
        AudioLogFactory(
            user=user, current_time=0, updated=timezone.now(), episode=episode
        )
        assert Episode.objects.with_current_time(user).first().get_pc_completed() == 0

    def test_get_pc_complete_gt_100(self, user):
        episode = EpisodeFactory(duration="100")
        AudioLogFactory(
            user=user, current_time=120, updated=timezone.now(), episode=episode
        )
        assert Episode.objects.with_current_time(user).first().get_pc_completed() == 100

    def test_get_pc_complete_marked_complete(self, user):
        now = timezone.now()
        episode = EpisodeFactory(duration="100")
        AudioLogFactory(
            user=user, current_time=50, updated=now, completed=now, episode=episode
        )
        assert Episode.objects.with_current_time(user).first().get_pc_completed() == 100

    def test_get_pc_complete_not_played(self, user):
        EpisodeFactory(duration="100")
        assert Episode.objects.with_current_time(user).first().get_pc_completed() == 0

    def test_get_pc_complete_anonymous(self, user, anonymous_user):
        episode = EpisodeFactory(duration="100")
        AudioLogFactory(
            user=user, current_time=50, updated=timezone.now(), episode=episode
        )
        assert (
            Episode.objects.with_current_time(anonymous_user).first().get_pc_completed()
            == 0
        )

    def is_favorited_anonymous(self, episode, anonymous_user):
        assert not episode.is_favorited(anonymous_user)

    def is_favorited_false(self, episode, user):
        assert not episode.is_favorited(user)

    def is_favorited_true(self):
        fave = FavoriteFactory()
        assert fave.episode.is_favorited(fave.user)

    def is_queued_anonymous(self, episode, anonymous_user):
        assert not episode.is_queued(anonymous_user)

    def is_queued_false(self, episode, user):
        assert not episode.is_queued(user)

    def is_queued_true(self):
        item = QueueItemFactory()
        assert item.episode.is_queued(item.user)

    def test_get_opengraph_data(self, rf, episode, site):
        req = rf.get("/")
        req.site = site
        data = episode.get_opengraph_data(req)
        assert episode.title in data["title"]
        assert data["url"] == "http://testserver" + episode.get_absolute_url()


class TestFavoriteManager:
    def test_search(self):
        episode = EpisodeFactory(title="testing")
        FavoriteFactory(episode=episode)
        assert Favorite.objects.search("testing").count() == 1

    def test_for_user_anonymous(self, anonymous_user):
        FavoriteFactory()
        assert Favorite.objects.for_user(anonymous_user).count() == 0

    def test_for_user(self, user):
        FavoriteFactory(user=user)
        assert Favorite.objects.for_user(user).count() == 1

    def test_create_favorite(self, user, episode):
        favorite, num_favorites = Favorite.objects.create_favorite(user, episode)
        assert favorite.episode == episode
        assert favorite.user == user
        assert num_favorites == 1


class TestAudioLogManager:
    def test_search(self):
        episode = EpisodeFactory(title="testing")
        AudioLogFactory(episode=episode)
        assert AudioLog.objects.search("testing").count() == 1


class TestQueueItemManager:
    def test_for_user_anonymous(self, anonymous_user):
        QueueItemFactory()
        assert QueueItem.objects.for_user(anonymous_user).count() == 0

    def test_for_user(self, user):
        QueueItemFactory(user=user)
        assert QueueItem.objects.for_user(user).count() == 1

    def test_create_item(self, user):
        episode = EpisodeFactory()
        item, num_items = QueueItem.objects.create_item(user, episode)
        assert item.episode == episode
        assert item.user == user
        assert item.position == 1
        assert num_items == 1

        episode = EpisodeFactory()
        item, num_items = QueueItem.objects.create_item(user, episode)
        assert item.episode == episode
        assert item.user == user
        assert item.position == 2
        assert num_items == 2

    def test_delete_item(self, user, episode):
        QueueItemFactory(user=user, episode=episode)
        assert QueueItem.objects.delete_item(user, episode) == 0

    def test_move_items(self, user):
        item_1 = QueueItemFactory(user=user, position=1)
        item_2 = QueueItemFactory(user=user, position=2)
        item_3 = QueueItemFactory(user=user, position=3)

        QueueItem.objects.move_items(user, [item_3.id, item_1.id, item_2.id])
        items = QueueItem.objects.for_user(user).order_by("position")
        assert items[0] == item_3
        assert items[1] == item_1
        assert items[2] == item_2

    def test_with_current_time_if_not_played(self, user):
        QueueItemFactory(user=user)
        item = QueueItem.objects.with_current_time(user).first()
        assert item.current_time is None

    def test_with_current_time_if_played(self, user):
        log = AudioLogFactory(user=user, current_time=20, updated=timezone.now())
        QueueItemFactory(user=user, episode=log.episode)
        item = QueueItem.objects.with_current_time(user).first()
        assert item.current_time == 20
