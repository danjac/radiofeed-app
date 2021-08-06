from django.utils import timezone

from jcasts.episodes.factories import AudioLogFactory
from jcasts.episodes.signals import close_player, open_player


class TestOpenPlayer:
    def test_nothing_logged(self, rf, django_user_model, user):
        req = rf.get("/")
        req.session = {}

        open_player(sender=django_user_model, user=user, request=req)

        assert req.session == {}

    def test_has_completed_episode(self, rf, django_user_model, user):
        AudioLogFactory(user=user, completed=timezone.now())

        req = rf.get("/")
        req.session = {}

        open_player(sender=django_user_model, user=user, request=req)

        assert req.session == {}

    def test_has_unfinished_episode(self, rf, django_user_model, user):
        log = AudioLogFactory(user=user, completed=None)

        req = rf.get("/")
        req.session = {}

        open_player(sender=django_user_model, user=user, request=req)

        assert req.session == {"player": {"episode": log.episode_id}}


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
