from __future__ import annotations

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from django.test import RequestFactory

from audiotrails.common.typedefs import AnyUser
from audiotrails.episodes.factories import AudioLogFactory, QueueItemFactory
from audiotrails.episodes.models import AudioLog, Episode, QueueItem
from audiotrails.episodes.player import Player


class TestPlayer:
    def make_request(
        self,
        rf: RequestFactory,
        episode: Episode | None = None,
        user: AnyUser | None = None,
    ) -> HttpRequest:
        req = rf.get("/")
        req.session = {}
        if episode is not None:
            req.session[Player.session_key] = {
                "episode": episode.id,
            }
        req.user = user or AnonymousUser()
        return req

    def test_start_episode(self, rf, episode, user):
        req = self.make_request(rf, user=user)

        player = Player(req)
        assert player.start_episode(episode).current_time == 0
        assert player.is_playing(episode)

        log = AudioLog.objects.get()

        assert log.episode == episode
        assert log.user == user
        assert log.current_time == 0

        assert not log.completed
        assert log.updated

    def test_start_episode_from_queue(self, rf, episode, user):
        req = self.make_request(rf, user=user)
        player = Player(req)

        QueueItemFactory(episode=episode, user=user)

        assert player.start_episode(episode).current_time == 0
        assert player.is_playing(episode)

        log = AudioLog.objects.get()

        assert log.episode == episode
        assert log.user == user
        assert log.current_time == 0

        assert not log.completed
        assert log.updated

        assert not QueueItem.objects.exists()

    def test_start_episode_already_played(self, rf, episode, user):

        log = AudioLogFactory(episode=episode, user=user, current_time=500)

        req = self.make_request(rf, user=user)

        player = Player(req)

        assert player.start_episode(episode).current_time == 500
        assert player.is_playing(episode)

        log.refresh_from_db()

        assert log.episode == episode
        assert log.user == user
        assert log.current_time == 500

        assert log.updated
        assert not log.completed

    def test_stop_episode_empty(self, rf, user):
        req = self.make_request(rf, user=user)

        player = Player(req)
        assert player.stop_episode() is None

    def test_stop_episode_not_in_session(self, rf, episode, user):

        AudioLogFactory(episode=episode, user=user)

        req = self.make_request(rf, user=user)

        player = Player(req)

        assert player.stop_episode() is None

    def test_stop_episode_in_session(self, rf, episode, user):

        log = AudioLogFactory(episode=episode, user=user)

        req = self.make_request(rf, episode=log.episode, user=user)

        player = Player(req)

        assert player.stop_episode() == log
        assert not player.is_playing(log.episode)

    def test_stop_episode_mark_complete(self, rf, episode, user):

        log = AudioLogFactory(episode=episode, user=user)

        req = self.make_request(rf, episode=log.episode, user=user)
        player = Player(req)

        assert player.stop_episode(mark_completed=True) == log
        assert not player.is_playing(log.episode)

        log.refresh_from_db()
        assert log.completed

    def test_update_current_time_not_playing(self, rf, episode, user):
        req = self.make_request(rf, user=user)

        player = Player(req)
        player.update_current_time(600)
        assert AudioLog.objects.count() == 0

    def test_update_current_time(self, rf, episode, user):

        log = AudioLogFactory(episode=episode, user=user, current_time=500)

        req = self.make_request(rf, episode=log.episode, user=user)

        player = Player(req)
        player.update_current_time(600)

        log.refresh_from_db()
        assert log.current_time == 600
