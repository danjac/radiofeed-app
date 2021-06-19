import datetime

from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.models import Site
from django.db import IntegrityError, transaction
from django.test import RequestFactory, SimpleTestCase, TestCase, TransactionTestCase
from django.utils import timezone

from audiotrails.episodes.factories import (
    AudioLogFactory,
    EpisodeFactory,
    FavoriteFactory,
    QueueItemFactory,
)
from audiotrails.episodes.models import AudioLog, Episode, Favorite, QueueItem
from audiotrails.users.factories import UserFactory


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
    def test_time_remaining(self) -> None:
        episode = Episode(duration="1:00:00")
        episode.current_time = 1200
        self.assertEqual(episode.get_time_remaining(), 2400)

    def test_time_remaining_current_time_none(self) -> None:
        episode = Episode(duration="1:00:00")
        episode.current_time = None
        self.assertEqual(episode.get_time_remaining(), 3600)

    def test_time_remaining_current_time_not_set(self) -> None:
        episode = Episode(duration="1:00:00")
        self.assertEqual(episode.get_time_remaining(), 3600)

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


class EpisodeCompleteModelTests(TransactionTestCase):
    def setUp(self) -> None:
        self.user = UserFactory()
        self.episode = EpisodeFactory(duration="100")

    def test_is_completed_if_not_set(self) -> None:
        self.assertFalse(self.episode.is_completed())

    def test_is_completed_if_marked_complete(self) -> None:
        AudioLogFactory(
            user=self.user,
            current_time=50,
            updated=timezone.now(),
            completed=timezone.now(),
            episode=self.episode,
        )
        self.assertTrue(
            Episode.objects.with_current_time(self.user).first().is_completed()
        )

    def test_is_completed_if_pc_complete_under_100(self) -> None:
        AudioLogFactory(
            user=self.user,
            current_time=50,
            updated=timezone.now(),
            episode=self.episode,
        )
        self.assertFalse(
            Episode.objects.with_current_time(self.user).first().is_completed()
        )

    def test_is_completed_if_pc_complete_over_100(self) -> None:
        AudioLogFactory(
            user=self.user,
            current_time=100,
            updated=timezone.now(),
            episode=self.episode,
        )
        self.assertTrue(
            Episode.objects.with_current_time(self.user).first().is_completed()
        )

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
            Episode.objects.with_current_time(self.user).first().get_pc_completed(),
            50,
        )

    def test_get_pc_complete_zero_current_time(self) -> None:
        AudioLogFactory(
            user=self.user,
            current_time=0,
            updated=timezone.now(),
            episode=self.episode,
        )
        self.assertEqual(
            Episode.objects.with_current_time(self.user).first().get_pc_completed(),
            0,
        )

    def test_get_pc_complete_zero_duration(self) -> None:
        AudioLogFactory(
            user=self.user,
            current_time=0,
            updated=timezone.now(),
            episode=EpisodeFactory(duration=""),
        )
        self.assertEqual(
            Episode.objects.with_current_time(self.user).first().get_pc_completed(),
            0,
        )

    def test_get_pc_complete_gt_100(self) -> None:
        AudioLogFactory(
            user=self.user,
            current_time=120,
            updated=timezone.now(),
            episode=self.episode,
        )
        self.assertEqual(
            Episode.objects.with_current_time(self.user).first().get_pc_completed(),
            100,
        )

    def test_get_pc_complete_marked_complete(self) -> None:
        now = timezone.now()
        user = UserFactory()
        AudioLogFactory(
            user=user,
            current_time=50,
            updated=now,
            completed=now,
            episode=self.episode,
        )
        self.assertEqual(
            Episode.objects.with_current_time(user).first().get_pc_completed(),
            100,
        )

    def test_get_pc_complete_not_played(self) -> None:
        user = UserFactory()
        self.assertEqual(
            Episode.objects.with_current_time(user).first().get_pc_completed(),
            0,
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

    def test_str(self):
        self.assertEqual(str(self.episode), self.episode.title)

    def test_str_no_title(self):
        episode = EpisodeFactory(title="")
        self.assertEqual(str(episode), episode.guid)

    def test_get_file_size(self):
        self.assertEqual(Episode(length=500).get_file_size(), "500\xa0bytes")

    def test_get_file_size_if_none(self):
        self.assertEqual(Episode(length=None).get_file_size(), None)

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

    def test_is_favorited_anonymous(self) -> None:
        self.assertFalse(self.episode.is_favorited(AnonymousUser()))

    def test_is_favorited_false(self) -> None:
        self.assertFalse(self.episode.is_favorited(self.user))

    def test_is_favorited_true(self) -> None:
        fave = FavoriteFactory(user=self.user, episode=self.episode)
        self.assertTrue(fave.episode.is_favorited(fave.user))

    def test_is_queued_anonymous(self) -> None:
        self.assertFalse(self.episode.is_queued(AnonymousUser()))

    def test_is_queued_false(self) -> None:
        self.assertFalse(self.episode.is_queued(self.user))

    def test_is_queued_true(self) -> None:
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


class AudioLogModelTests(TestCase):
    def test_to_json(self):
        log = AudioLogFactory()
        data = log.to_json()
        self.assertEqual(data["episode"]["id"], log.episode.id)
        self.assertEqual(data["episode"]["url"], log.episode.get_absolute_url())
        self.assertEqual(data["podcast"]["title"], log.episode.podcast.title)
        self.assertEqual(data["podcast"]["url"], log.episode.podcast.get_absolute_url())


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

    def test_move_items(self) -> None:
        first = QueueItemFactory(user=self.user)
        second = QueueItemFactory(user=self.user)
        third = QueueItemFactory(user=self.user)

        items = QueueItem.objects.filter(user=self.user).order_by("position")

        self.assertEqual(items[0], first)
        self.assertEqual(items[1], second)
        self.assertEqual(items[2], third)

        QueueItem.objects.move_items(self.user, [third.id, first.id, second.id])

        items = QueueItem.objects.filter(user=self.user).order_by("position")

        self.assertEqual(items[0], third)
        self.assertEqual(items[1], first)
        self.assertEqual(items[2], second)

    def test_add_item_to_start_empty(self) -> None:
        episode = EpisodeFactory()
        item = QueueItem.objects.add_item_to_start(self.user, episode)
        self.assertEqual(item.episode, episode)
        self.assertEqual(item.user, self.user)
        self.assertEqual(item.position, 1)

    def test_add_item_to_start_other_items(self) -> None:
        other = QueueItemFactory(user=self.user, position=1)

        episode = EpisodeFactory()
        item = QueueItem.objects.add_item_to_start(self.user, episode)

        self.assertEqual(item.episode, episode)
        self.assertEqual(item.user, self.user)
        self.assertEqual(item.position, 1)

        other.refresh_from_db()
        self.assertEqual(other.position, 2)

    def test_add_item_to_start_already_exists(self) -> None:
        other = QueueItemFactory(user=self.user, position=1)

        with transaction.atomic():
            self.assertRaises(
                IntegrityError,
                QueueItem.objects.add_item_to_start,
                self.user,
                other.episode,
            )
        self.assertEqual(QueueItem.objects.count(), 1)

        other.refresh_from_db()
        self.assertEqual(other.position, 1)

    def test_add_item_to_end_empty(self) -> None:
        episode = EpisodeFactory()
        item = QueueItem.objects.add_item_to_end(self.user, episode)
        self.assertEqual(item.episode, episode)
        self.assertEqual(item.user, self.user)
        self.assertEqual(item.position, 1)

    def test_add_item_to_end_other_items(self) -> None:
        QueueItemFactory(user=self.user, position=1)

        episode = EpisodeFactory()
        item = QueueItem.objects.add_item_to_end(self.user, episode)

        self.assertEqual(item.episode, episode)
        self.assertEqual(item.user, self.user)
        self.assertEqual(item.position, 2)

    def test_add_item_to_end_already_exists(self) -> None:
        other = QueueItemFactory(user=self.user, position=1)

        with transaction.atomic():
            self.assertRaises(
                IntegrityError,
                QueueItem.objects.add_item_to_end,
                self.user,
                other.episode,
            )
        self.assertEqual(QueueItem.objects.count(), 1)

        other.refresh_from_db()
        self.assertEqual(other.position, 1)
