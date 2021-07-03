from __future__ import annotations

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from django.test import RequestFactory, TestCase

from audiotrails.common.typedefs import AnyUser
from audiotrails.episodes.factories import (
    AudioLogFactory,
    EpisodeFactory,
    QueueItemFactory,
)
from audiotrails.episodes.models import AudioLog, Episode, QueueItem
from audiotrails.episodes.player import Player
from audiotrails.users.factories import UserFactory


class PlayerTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.episode = EpisodeFactory()
        cls.user = UserFactory()

    def setUp(self) -> None:
        self.rf = RequestFactory()

    def make_request(
        self,
        episode: Episode | None = None,
        user: AnyUser | None = None,
        is_queued: bool = False,
    ) -> HttpRequest:
        req = self.rf.get("/")
        req.session = {}
        if episode is not None:
            req.session[Player.session_key] = {
                "episode": episode.id,
            }
        req.user = user or AnonymousUser()
        return req

    def test_start_episode(self) -> None:
        req = self.make_request(user=self.user)
        player = Player(req)

        self.assertEqual(player.start_episode(self.episode).current_time, 0)

        log = AudioLog.objects.get()

        self.assertEqual(log.episode, self.episode)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.current_time, 0)

        self.assertFalse(log.completed)
        self.assertTrue(log.updated)

        self.assertTrue(player.is_playing(self.episode))

    def test_start_episode_from_queue(self) -> None:
        req = self.make_request(user=self.user)
        player = Player(req)

        QueueItemFactory(episode=self.episode, user=self.user)

        self.assertEqual(player.start_episode(self.episode).current_time, 0)

        log = AudioLog.objects.get()

        self.assertEqual(log.episode, self.episode)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.current_time, 0)

        self.assertFalse(log.completed)
        self.assertTrue(log.updated)

        self.assertTrue(player.is_playing(self.episode))
        self.assertFalse(QueueItem.objects.exists())

    def test_start_episode_already_played(self) -> None:

        log = AudioLogFactory(episode=self.episode, user=self.user, current_time=500)

        req = self.make_request(user=self.user)

        player = Player(req)
        self.assertEqual(player.start_episode(self.episode).current_time, 500)

        log.refresh_from_db()

        self.assertEqual(log.episode, self.episode)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.current_time, 500)

        self.assertTrue(log.updated)
        self.assertFalse(log.completed)

        self.assertTrue(player.is_playing(self.episode))

    def test_stop_episode_empty(self) -> None:
        req = self.make_request(user=self.user)

        player = Player(req)
        self.assertEqual(player.stop_episode(), None)

    def test_stop_episode_not_in_session(self) -> None:

        AudioLogFactory(episode=self.episode, user=self.user)

        req = self.make_request(user=self.user)

        player = Player(req)

        self.assertEqual(player.stop_episode(), None)

    def test_stop_episode_in_session(self) -> None:

        log = AudioLogFactory(episode=self.episode, user=self.user)

        req = self.make_request(episode=log.episode, user=self.user)

        player = Player(req)

        self.assertEqual(player.stop_episode(), log)
        self.assertFalse(player.is_playing(log.episode))

    def test_stop_episode_mark_complete(self) -> None:

        log = AudioLogFactory(episode=self.episode, user=self.user)

        req = self.make_request(episode=log.episode, user=self.user)
        player = Player(req)

        self.assertEqual(player.stop_episode(mark_completed=True), log)
        self.assertFalse(player.is_playing(log.episode))

        log.refresh_from_db()
        self.assertTrue(log.completed)

    def test_update_current_time_not_playing(self) -> None:
        req = self.make_request(user=self.user)

        player = Player(req)
        player.update_current_time(600)
        self.assertEqual(AudioLog.objects.count(), 0)

    def test_update_current_time(self) -> None:

        log = AudioLogFactory(episode=self.episode, user=self.user, current_time=500)

        req = self.make_request(episode=log.episode, user=self.user)

        player = Player(req)
        player.update_current_time(600)

        log.refresh_from_db()
        self.assertEqual(log.current_time, 600)
