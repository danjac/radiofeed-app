from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from audiotrails.users.factories import UserFactory

from ..factories import AudioLogFactory, EpisodeFactory
from ..player import Player
from ..templatetags.player import get_player


class GetPlayerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.episode = EpisodeFactory()
        cls.user = UserFactory()

    def setUp(self):
        self.rf = RequestFactory()

    def test_anonymous(self):
        req = self.rf.get("/")
        req.user = AnonymousUser()
        req.session = {}
        req.player = Player(req)
        self.assertEqual(get_player({"request": req}), {})

    def test_player_not_loaded(self):
        req = self.rf.get("/")
        req.user = self.user
        req.session = {}
        req.player = Player(req)
        self.assertEqual(get_player({"request": req}), {})

    def test_player_loaded(self):
        AudioLogFactory(user=self.user, episode=self.episode, current_time=300)
        req = self.rf.get("/")
        req.user = self.user
        req.session = {"player_episode": self.episode.id}
        req.player = Player(req)
        self.assertEqual(
            get_player({"request": req}),
            {
                "episode": self.episode,
                "current_time": 300,
            },
        )
