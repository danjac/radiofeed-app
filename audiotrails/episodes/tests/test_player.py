import pytest

from ..models import AudioLog
from ..player import Player

pytestmark = pytest.mark.django_db


class TestPlayer:
    def test_start_episode(self, rf, user, episode):
        req = rf.get("/")
        req.session = {}
        req.user = user
        req.episode = episode
        player = Player(req)
        player.start_episode(episode)

        log = AudioLog.objects.get()
        assert log.episode == episode
        assert log.user == user
        assert log.updated
        assert not log.completed

        assert player.is_playing(episode)
