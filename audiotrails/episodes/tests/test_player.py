import pytest

from ..factories import AudioLogFactory
from ..player import Player

pytestmark = pytest.mark.django_db


class TestPlayer:
    def make_player(self, rf, user=None, session=None):
        req = rf.get("/")
        req.user = user
        req.session = session or {}
        return Player(req)

    def test_empty(self, rf, user):
        player = self.make_player(rf, user)
        assert not player
        assert player.episode is None
        assert player.current_time == 0
        assert player.playback_rate == 1.0

    def test_not_empty(self, rf, user, episode):
        AudioLogFactory(
            user=user,
            episode=episode,
            current_time=1000,
        )
        player = self.make_player(
            rf, user, {"player_episode": episode.id, "player_playback_rate": 1.2}
        )
        assert player
        assert player.episode == episode
        assert player.current_time == 1000
        assert player.playback_rate == 1.2

    def test_eject(self, rf, user, episode):
        log = AudioLogFactory(
            user=user,
            episode=episode,
            current_time=1000,
        )
        session = {"player_episode": episode.id, "player_playback_rate": 1.2}
        player = self.make_player(rf, user, session)

        assert player.current_time == 1000
        assert player.playback_rate == 1.2

        current_episode = player.eject()

        assert current_episode == episode

        assert not player
        assert player.current_time == 0
        assert player.playback_rate == 1.2

        log.refresh_from_db()

        assert not log.completed
        assert "player_episode" not in session

    def test_eject_and_mark_completed(self, rf, user, episode):
        log = AudioLogFactory(
            user=user,
            episode=episode,
            current_time=1000,
        )

        session = {"player_episode": episode.id, "player_playback_rate": 1.2}

        player = self.make_player(rf, user, session)

        assert player.current_time == 1000
        assert player.playback_rate == 1.2

        current_episode = player.eject(mark_completed=True)

        assert current_episode == episode

        assert not player

        assert player.current_time == 0
        assert player.playback_rate == 1.2
        assert player.episode is None

        log.refresh_from_db()
        assert log.completed
        assert log.current_time == 0

        assert "player_episode" not in session

    def test_is_playing_true(self, rf, episode, user):
        AudioLogFactory(
            user=user,
            episode=episode,
            current_time=1000,
        )
        player = self.make_player(rf, user, {"player_episode": episode.id})

        assert player.is_playing(episode)

    def test_is_playing_anonymous(self, rf, episode, anonymous_user):
        AudioLogFactory(
            episode=episode,
            current_time=1000,
        )
        player = self.make_player(rf, anonymous_user, {"player_episode": episode.id})

        assert not player.is_playing(episode)

    def test_is_playing_false(self, rf, episode, user):
        AudioLogFactory(
            episode=episode,
            current_time=1000,
        )
        player = self.make_player(rf, user)

        assert not player.is_playing(episode)

    def test_is_playing_empty(self, rf, episode, user):
        player = self.make_player(rf, user=user)
        assert not player.is_playing(episode)
