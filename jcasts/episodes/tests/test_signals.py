import pytest

from django.utils import timezone

from jcasts.episodes.factories import AudioLogFactory
from jcasts.episodes.player import Player
from jcasts.episodes.signals import close_player, open_player


class TestOpenPlayer:
    @pytest.fixture
    def req(self, rf):
        req = rf.get("/")
        req.session = {}
        req.player = Player(req)
        return req

    def test_nothing_logged(self, req, django_user_model, user):

        open_player(sender=django_user_model, user=user, request=req)

        assert req.player.get_episode() is None

    def test_has_completed_episode(self, req, django_user_model, user):
        AudioLogFactory(user=user, completed=timezone.now())

        open_player(sender=django_user_model, user=user, request=req)

        assert req.player.get_episode() is None

    def test_has_unfinished_episode_autoplay_off(self, req, django_user_model, user):
        AudioLogFactory(user=user, completed=None, autoplay=False)

        open_player(sender=django_user_model, user=user, request=req)

        assert req.player.get_episode() is None

    def test_has_unfinished_episode(self, req, django_user_model, user):
        log = AudioLogFactory(user=user, completed=None, autoplay=True)

        open_player(sender=django_user_model, user=user, request=req)

        assert req.player.get_episode() == log.episode.id


class TestClosePlayer:
    def test_nothing_logged(self, rf, django_user_model, anonymous_user):
        req = rf.get("/")
        req.session = {}

        close_player(sender=django_user_model, user=anonymous_user, request=req)

        assert req.session == {}

    def test_has_episode(self, rf, django_user_model, user, anonymous_user):
        log = AudioLogFactory(user=user)

        req = rf.get("/")
        req.session = {"player": {"episode": log.episode_id}}

        close_player(sender=django_user_model, user=anonymous_user, request=req)

        assert req.session == {}
