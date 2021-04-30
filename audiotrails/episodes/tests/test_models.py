import datetime

from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.models import Site
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.utils import timezone

from audiotrails.users.factories import UserFactory

from ..factories import (
    AudioLogFactory,
    EpisodeFactory,
    FavoriteFactory,
    QueueItemFactory,
)
from ..models import AudioLog, Episode, Favorite, QueueItem


class EpisodeManagerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def test_with_current_time_if_anonymous(self):
        EpisodeFactory()
        episode = Episode.objects.with_current_time(AnonymousUser()).first()
        self.assertEqual(episode.current_time, 0)
        self.assertFalse(episode.completed)
        self.assertFalse(episode.listened)

    def test_with_current_time_if_not_played(self):
        EpisodeFactory()
        episode = Episode.objects.with_current_time(self.user).first()
        self.assertFalse(episode.current_time)
        self.assertFalse(episode.completed)
        self.assertFalse(episode.listened)

    def test_with_current_time_if_played(self):
        log = AudioLogFactory(user=self.user, current_time=20, updated=timezone.now())
        episode = Episode.objects.with_current_time(self.user).first()
        self.assertEqual(episode.current_time, 20)
        self.assertFalse(episode.completed)
        self.assertEqual(episode.listened, log.updated)

    def test_with_current_time_if_completed(self):
        log = AudioLogFactory(
            user=self.user,
            current_time=20,
            completed=timezone.now(),
            updated=timezone.now(),
        )
        episode = Episode.objects.with_current_time(self.user).first()
        self.assertEqual(episode.current_time, 20)
        self.assertTrue(episode.completed)
        self.assertEqual(episode.listened, log.updated)

    def test_search(self):
        EpisodeFactory(title="testing")
        self.assertEqual(Episode.objects.search("testing").count(), 1)


class SimpleEpisodeModelTests(SimpleTestCase):
    # no db required
    def test_duration_in_seconds_if_empty_or_none(self):
        self.assertEqual(Episode(duration=None).get_duration_in_seconds(), 0)
        self.assertEqual(Episode(duration="").get_duration_in_seconds(), 0)

    def test_duration_in_seconds_invalid_string(self):
        self.assertEqual(Episode(duration="oops").get_duration_in_seconds(), 0)

    def test_duration_in_seconds_hours_minutes_seconds(self):
        self.assertEqual(Episode(duration="2:30:40").get_duration_in_seconds(), 9040)

    def test_duration_in_seconds_hours_minutes_seconds_extra_digit(self):
        self.assertEqual(
            Episode(duration="2:30:40:2903903").get_duration_in_seconds(), 9040
        )

    def test_duration_in_seconds_minutes_seconds(self):
        self.assertEqual(Episode(duration="30:40").get_duration_in_seconds(), 1840)

    def test_duration_in_seconds_seconds_only(self):
        self.assertEqual(Episode(duration="40").get_duration_in_seconds(), 40)

    def test_slug(self):
        episode = Episode(title="Testing")
        self.assertEqual(episode.slug, "testing")

    def test_slug_if_title_empty(self):
        self.assertEqual(Episode().slug, "episode")

    def test_get_duration_in_seconds_if_empty(self):
        self.assertEqual(Episode().get_duration_in_seconds(), 0)
        self.assertEqual(Episode(duration="").get_duration_in_seconds(), 0)

    def test_duration_in_seconds_if_non_numeric(self):
        self.assertEqual(Episode(duration="NaN").get_duration_in_seconds(), 0)

    def test_duration_in_seconds_if_seconds_only(self):
        self.assertEqual(Episode(duration="60").get_duration_in_seconds(), 60)

    def test_duration_in_seconds_if_minutes_and_seconds(self):
        self.assertEqual(Episode(duration="2:30").get_duration_in_seconds(), 150)

    def test_duration_in_seconds_if_hours_minutes_and_seconds(self):
        self.assertEqual(Episode(duration="2:30:30").get_duration_in_seconds(), 9030)


class EpisodePcCompleteModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def test_get_pc_complete_without_current_time_attr(self):
        episode = EpisodeFactory(duration="100")
        AudioLogFactory(
            user=self.user, current_time=50, updated=timezone.now(), episode=episode
        )
        self.assertEqual(Episode.objects.first().get_pc_completed(), 0)

    def test_get_pc_complete(self):
        episode = EpisodeFactory(duration="100")
        AudioLogFactory(
            user=self.user, current_time=50, updated=timezone.now(), episode=episode
        )
        self.assertEqual(
            Episode.objects.with_current_time(self.user).first().get_pc_completed(), 50
        )

    def test_get_pc_complete_zero_current_time(self):
        episode = EpisodeFactory(duration="100")
        AudioLogFactory(
            user=self.user, current_time=0, updated=timezone.now(), episode=episode
        )
        self.assertEqual(
            Episode.objects.with_current_time(self.user).first().get_pc_completed(), 0
        )

    def test_get_pc_complete_zero_duration(self):
        episode = EpisodeFactory(duration="")
        AudioLogFactory(
            user=self.user, current_time=0, updated=timezone.now(), episode=episode
        )
        self.assertEqual(
            Episode.objects.with_current_time(self.user).first().get_pc_completed(), 0
        )

    def test_get_pc_complete_gt_100(self):
        episode = EpisodeFactory(duration="100")
        AudioLogFactory(
            user=self.user, current_time=120, updated=timezone.now(), episode=episode
        )
        self.assertEqual(
            Episode.objects.with_current_time(self.user).first().get_pc_completed(), 100
        )

    def test_get_pc_complete_marked_complete(self):
        now = timezone.now()
        episode = EpisodeFactory(duration="100")
        user = UserFactory()
        AudioLogFactory(
            user=user, current_time=50, updated=now, completed=now, episode=episode
        )
        self.assertEqual(
            Episode.objects.with_current_time(user).first().get_pc_completed(), 100
        )

    def test_get_pc_complete_not_played(self):
        user = UserFactory()
        EpisodeFactory(duration="100")
        self.assertEqual(
            Episode.objects.with_current_time(user).first().get_pc_completed(), 0
        )

    def test_get_pc_complete_anonymous(self):
        episode = EpisodeFactory(duration="100")
        AudioLogFactory(
            user=UserFactory(), current_time=50, updated=timezone.now(), episode=episode
        )
        self.assertEqual(
            Episode.objects.with_current_time(AnonymousUser())
            .first()
            .get_pc_completed(),
            0,
        )


class EpisodeInstanceModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.episode = EpisodeFactory()

    def test_get_media_metadata(self):
        data = self.episode.get_media_metadata()
        self.assertEqual(data["title"], self.episode.title)
        self.assertEqual(data["album"], self.episode.podcast.title)
        self.assertEqual(data["artist"], self.episode.podcast.creators)

    def test_has_next_previous_episode(self):
        self.assertEqual(self.episode.get_next_episode(), None)
        self.assertEqual(self.episode.get_previous_episode(), None)

        next_episode = EpisodeFactory(
            podcast=self.episode.podcast,
            pub_date=self.episode.pub_date + datetime.timedelta(days=2),
        )

        previous_episode = EpisodeFactory(
            podcast=self.episode.podcast,
            pub_date=self.episode.pub_date - datetime.timedelta(days=2),
        )

        EpisodeFactory(
            podcast=self.episode.podcast,
            pub_date=self.episode.pub_date - datetime.timedelta(days=3),
        )

        self.assertEqual(self.episode.get_next_episode(), next_episode)
        self.assertEqual(self.episode.get_previous_episode(), previous_episode)

    def is_favorited_anonymous(self):
        self.assertFalse(self.episode.is_favorited(AnonymousUser()))

    def is_favorited_false(self):
        self.assertFalse(self.episode.is_favorited(self.user))

    def is_favorited_true(self):
        fave = FavoriteFactory(user=self.user, episode=self.episode)
        self.assertTrue(fave.episode.is_favorited(fave.user))

    def is_queued_anonymous(self):
        self.assertFalse(self.episode.is_queued(AnonymousUser()))

    def is_queued_false(self):
        self.assertFalse(self.episode.is_queued(self.user))

    def is_queued_true(self):
        item = QueueItemFactory(user=self.user, episode=self.episode)
        self.assertTrue(item.episode.is_queued(item.user))

    def test_get_opengraph_data(self):
        req = RequestFactory().get("/")
        req.site = Site.objects.get_current()
        data = self.episode.get_opengraph_data(req)
        self.assertTrue(self.episode.title in data["title"])
        self.assertEqual(
            data["url"], "http://testserver" + self.episode.get_absolute_url()
        )


class TestFavoriteManager:
    def test_search(self):
        episode = EpisodeFactory(title="testing")
        FavoriteFactory(episode=episode)
        assert Favorite.objects.search("testing").count() == 1


class TestAudioLogManager:
    def test_search(self):
        episode = EpisodeFactory(title="testing")
        AudioLogFactory(episode=episode)
        assert AudioLog.objects.search("testing").count() == 1


class TestQueueItemManager:
    def test_with_current_time_if_not_played(self, user):
        QueueItemFactory(user=user)
        item = QueueItem.objects.with_current_time(user).first()
        assert item.current_time is None

    def test_with_current_time_if_played(self, user):
        log = AudioLogFactory(user=user, current_time=20, updated=timezone.now())
        QueueItemFactory(user=user, episode=log.episode)
        item = QueueItem.objects.with_current_time(user).first()
        assert item.current_time == 20
