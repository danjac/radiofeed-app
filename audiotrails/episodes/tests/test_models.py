import datetime

from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.models import Site
from django.test import RequestFactory, SimpleTestCase, TestCase, TransactionTestCase
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
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()

    def test_with_current_time_if_anonymous(self) -> None:
        EpisodeFactory()
        episode = Episode.objects.with_current_time(AnonymousUser()).first()
        self.assertEqual(episode.current_time, 0)
        self.assertFalse(episode.completed)
        self.assertFalse(episode.listened)

    def test_with_current_time_if_not_played(self) -> None:
        EpisodeFactory()
        episode = Episode.objects.with_current_time(self.user).first()
        self.assertFalse(episode.current_time)
        self.assertFalse(episode.completed)
        self.assertFalse(episode.listened)

    def test_with_current_time_if_played(self) -> None:
        log = AudioLogFactory(user=self.user, current_time=20, updated=timezone.now())
        episode = Episode.objects.with_current_time(self.user).first()
        self.assertEqual(episode.current_time, 20)
        self.assertFalse(episode.completed)
        self.assertEqual(episode.listened, log.updated)

    def test_with_current_time_if_completed(self) -> None:
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


class EpisodeManagerSearchTests(TransactionTestCase):
    def test_search(self) -> None:
        EpisodeFactory(title="testing")
        self.assertEqual(Episode.objects.search("testing").count(), 1)


class EpisodeDurationTests(SimpleTestCase):
    def test_duration_in_seconds_if_empty_or_none(self) -> None:
        self.assertEqual(Episode(duration=None).get_duration_in_seconds(), 0)
        self.assertEqual(Episode(duration="").get_duration_in_seconds(), 0)

    def test_duration_in_seconds_invalid_string(self) -> None:
        self.assertEqual(Episode(duration="oops").get_duration_in_seconds(), 0)

    def test_duration_in_seconds_hours_minutes_seconds(self):
        self.assertEqual(Episode(duration="2:30:40").get_duration_in_seconds(), 9040)

    def test_duration_in_seconds_hours_minutes_seconds_extra_digit(self):
        self.assertEqual(
            Episode(duration="2:30:40:2903903").get_duration_in_seconds(), 9040
        )

    def test_duration_in_seconds_minutes_seconds(self) -> None:
        self.assertEqual(Episode(duration="30:40").get_duration_in_seconds(), 1840)

    def test_duration_in_seconds_seconds_only(self) -> None:
        self.assertEqual(Episode(duration="40").get_duration_in_seconds(), 40)

    def test_get_duration_in_seconds_if_empty(self) -> None:
        self.assertEqual(Episode().get_duration_in_seconds(), 0)
        self.assertEqual(Episode(duration="").get_duration_in_seconds(), 0)

    def test_duration_in_seconds_if_non_numeric(self) -> None:
        self.assertEqual(Episode(duration="NaN").get_duration_in_seconds(), 0)

    def test_duration_in_seconds_if_seconds_only(self) -> None:
        self.assertEqual(Episode(duration="60").get_duration_in_seconds(), 60)

    def test_duration_in_seconds_if_minutes_and_seconds(self) -> None:
        self.assertEqual(Episode(duration="2:30").get_duration_in_seconds(), 150)

    def test_duration_in_seconds_if_hours_minutes_and_seconds(self) -> None:
        self.assertEqual(Episode(duration="2:30:30").get_duration_in_seconds(), 9030)


class EpisodeSlugTests(SimpleTestCase):
    def test_slug(self) -> None:
        episode = Episode(title="Testing")
        self.assertEqual(episode.slug, "testing")

    def test_slug_if_title_empty(self) -> None:
        self.assertEqual(Episode().slug, "episode")


class EpisodePcCompleteModelTests(TransactionTestCase):
    def setUp(self) -> None:
        self.user = UserFactory()
        self.episode = EpisodeFactory(duration="100")

    def test_get_pc_complete_without_current_time_attr(self) -> None:
        AudioLogFactory(
            user=self.user,
            current_time=50,
            updated=timezone.now(),
            episode=self.episode,
        )
        self.assertEqual(Episode.objects.first().get_pc_completed(), 0)

    def test_get_pc_complete(self) -> None:
        AudioLogFactory(
            user=self.user,
            current_time=50,
            updated=timezone.now(),
            episode=self.episode,
        )
        self.assertEqual(
            Episode.objects.with_current_time(self.user).first().get_pc_completed(), 50
        )

    def test_get_pc_complete_zero_current_time(self) -> None:
        AudioLogFactory(
            user=self.user, current_time=0, updated=timezone.now(), episode=self.episode
        )
        self.assertEqual(
            Episode.objects.with_current_time(self.user).first().get_pc_completed(), 0
        )

    def test_get_pc_complete_zero_duration(self) -> None:
        AudioLogFactory(
            user=self.user,
            current_time=0,
            updated=timezone.now(),
            episode=EpisodeFactory(duration=""),
        )
        self.assertEqual(
            Episode.objects.with_current_time(self.user).first().get_pc_completed(), 0
        )

    def test_get_pc_complete_gt_100(self) -> None:
        AudioLogFactory(
            user=self.user,
            current_time=120,
            updated=timezone.now(),
            episode=self.episode,
        )
        self.assertEqual(
            Episode.objects.with_current_time(self.user).first().get_pc_completed(), 100
        )

    def test_get_pc_complete_marked_complete(self) -> None:
        now = timezone.now()
        user = UserFactory()
        AudioLogFactory(
            user=user, current_time=50, updated=now, completed=now, episode=self.episode
        )
        self.assertEqual(
            Episode.objects.with_current_time(user).first().get_pc_completed(), 100
        )

    def test_get_pc_complete_not_played(self) -> None:
        user = UserFactory()
        self.assertEqual(
            Episode.objects.with_current_time(user).first().get_pc_completed(), 0
        )

    def test_get_pc_complete_anonymous(self) -> None:
        AudioLogFactory(
            user=UserFactory(),
            current_time=50,
            updated=timezone.now(),
            episode=self.episode,
        )
        self.assertEqual(
            Episode.objects.with_current_time(AnonymousUser())
            .first()
            .get_pc_completed(),
            0,
        )


class EpisodeModelTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()
        cls.episode = EpisodeFactory()

    def test_get_media_metadata(self) -> None:
        data = self.episode.get_media_metadata()
        self.assertEqual(data["title"], self.episode.title)
        self.assertEqual(data["album"], self.episode.podcast.title)
        self.assertEqual(data["artist"], self.episode.podcast.creators)

    def test_get_opengraph_data(self) -> None:
        req = RequestFactory().get("/")
        req.site = Site.objects.get_current()
        data = self.episode.get_opengraph_data(req)
        self.assertTrue(self.episode.title in data["title"])
        self.assertEqual(
            data["url"], "http://testserver" + self.episode.get_absolute_url()
        )

    def test_has_next_previous_episode(self) -> None:
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

    def is_favorited_anonymous(self) -> None:
        self.assertFalse(self.episode.is_favorited(AnonymousUser()))

    def is_favorited_false(self) -> None:
        self.assertFalse(self.episode.is_favorited(self.user))

    def is_favorited_true(self) -> None:
        fave = FavoriteFactory(user=self.user, episode=self.episode)
        self.assertTrue(fave.episode.is_favorited(fave.user))

    def is_queued_anonymous(self) -> None:
        self.assertFalse(self.episode.is_queued(AnonymousUser()))

    def is_queued_false(self) -> None:
        self.assertFalse(self.episode.is_queued(self.user))

    def is_queued_true(self) -> None:
        item = QueueItemFactory(user=self.user, episode=self.episode)
        self.assertTrue(item.episode.is_queued(item.user))


class FavoriteManagerTests(TestCase):
    def test_search(self) -> None:
        episode = EpisodeFactory(title="testing")
        FavoriteFactory(episode=episode)
        self.assertEqual(Favorite.objects.search("testing").count(), 1)


class AudioLogManagerTests(TestCase):
    def test_search(self) -> None:
        episode = EpisodeFactory(title="testing")
        AudioLogFactory(episode=episode)
        self.assertEqual(AudioLog.objects.search("testing").count(), 1)


class QueueItemManagerTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = UserFactory()

    def test_with_current_time_if_not_played(self) -> None:
        QueueItemFactory(user=self.user)
        item = QueueItem.objects.with_current_time(self.user).first()
        self.assertEqual(item.current_time, None)

    def test_with_current_time_if_played(self) -> None:
        log = AudioLogFactory(user=self.user, current_time=20, updated=timezone.now())
        QueueItemFactory(user=self.user, episode=log.episode)
        item = QueueItem.objects.with_current_time(self.user).first()
        self.assertEqual(item.current_time, 20)
