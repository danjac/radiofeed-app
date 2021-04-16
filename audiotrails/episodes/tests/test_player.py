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
            is_playing=True,
            current_time=1000,
        )
        player = self.make_player(
            rf,
            user=user,
            session={
                "player": {
                    "playback_rate": 1.2,
                }
            },
        )
        assert player
        assert player.episode == episode
        assert player.current_time == 1000
        assert player.playback_rate == 1.2

    def test_eject(self, rf, user, episode):
        log = AudioLogFactory(
            user=user,
            episode=episode,
            is_playing=True,
            current_time=1000,
        )
        session = {
            "player": {
                "playback_rate": 1.2,
            }
        }

        player = self.make_player(rf, user=user, session=session)

        assert player.current_time == 1000
        assert player.playback_rate == 1.2

        current_episode = player.eject()

        assert current_episode == episode

        assert not player
        assert player.current_time == 0
        assert player.playback_rate == 1.0

        log.refresh_from_db()

        assert not log.is_playing
        assert not log.completed

    def test_eject_and_mark_completed(self, rf, user, episode):
        log = AudioLogFactory(
            user=user,
            episode=episode,
            is_playing=True,
            current_time=1000,
        )
        session = {
            "player": {
                "playback_rate": 1.2,
            }
        }

        player = self.make_player(rf, user=user, session=session)

        assert player.current_time == 1000
        assert player.playback_rate == 1.2

        current_episode = player.eject(mark_completed=True)

        assert current_episode == episode

        assert not player
        assert player.current_time == 0
        assert player.playback_rate == 1.0

        log.refresh_from_db()
        assert log.completed
        assert log.current_time == 0

    def test_is_playing_true(self, rf, episode, user):
        AudioLogFactory(
            user=user,
            episode=episode,
            is_playing=True,
            current_time=1000,
        )
        player = self.make_player(
            rf,
            user=user,
        )

        assert player.is_playing(episode)

    def test_is_playing_anonymous(self, rf, episode, anonymous_user):
        AudioLogFactory(
            episode=episode,
            is_playing=True,
            current_time=1000,
        )
        player = self.make_player(
            rf,
            user=anonymous_user,
            session={
                "player": {
                    "playback_rate": 1.2,
                }
            },
        )

        assert not player.is_playing(episode)

    def test_is_playing_false(self, rf, episode, user):
        AudioLogFactory(
            episode=episode,
            is_playing=False,
            current_time=1000,
        )
        player = self.make_player(
            rf,
            user=user,
            session={
                "player": {
                    "playback_rate": 1.2,
                }
            },
        )

        assert not player.is_playing(episode)

    def test_is_playing_empty(self, rf, episode, user):
        player = self.make_player(rf, user=user)
        assert not player.is_playing(episode)
