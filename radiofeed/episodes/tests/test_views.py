# Standard Library
import json

# Django
from django.urls import reverse

# Third Party Libraries
import pytest

# RadioFeed
from radiofeed.podcasts.factories import SubscriptionFactory

# Local
from .. import views
from ..factories import AudioLogFactory, BookmarkFactory, EpisodeFactory
from ..models import AudioLog, Bookmark

pytestmark = pytest.mark.django_db


class TestEpisodeList:
    def test_anonymous(self, rf, anonymous_user):
        EpisodeFactory.create_batch(3)
        req = rf.get(reverse("episodes:episode_list"))
        req.user = anonymous_user
        resp = views.episode_list(req)
        assert resp.status_code == 200
        assert len(resp.context_data["episodes"]) == 3

    def test_user_no_subscriptions(self, rf, user):
        EpisodeFactory.create_batch(3)
        req = rf.get(reverse("episodes:episode_list"))
        req.user = user
        resp = views.episode_list(req)
        assert resp.status_code == 200
        assert len(resp.context_data["episodes"]) == 3

    def test_user_has_subscriptions(self, rf, user):
        EpisodeFactory.create_batch(3)

        episode = EpisodeFactory()
        SubscriptionFactory(user=user, podcast=episode.podcast)

        req = rf.get(reverse("episodes:episode_list"))
        req.user = user
        resp = views.episode_list(req)

        assert resp.status_code == 200
        assert len(resp.context_data["episodes"]) == 1
        assert resp.context_data["episodes"][0] == episode

    def test_anonymous_search(self, rf, anonymous_user):
        EpisodeFactory.create_batch(3, title="zzzz", keywords="zzzz")
        episode = EpisodeFactory(title="testing")
        req = rf.get(reverse("episodes:episode_list"), {"q": "testing"})
        req.user = anonymous_user
        resp = views.episode_list(req)
        assert resp.status_code == 200
        assert len(resp.context_data["episodes"]) == 1
        assert resp.context_data["episodes"][0] == episode

    def test_user_has_subscriptions_search(self, rf, user):
        "Ignore subs in search"
        EpisodeFactory.create_batch(3, title="zzzz", keywords="zzzz")
        SubscriptionFactory(user=user, podcast=EpisodeFactory().podcast)
        episode = EpisodeFactory(title="testing")
        req = rf.get(reverse("episodes:episode_list"), {"q": "testing"})
        req.user = user
        resp = views.episode_list(req)
        assert resp.status_code == 200
        assert len(resp.context_data["episodes"]) == 1
        assert resp.context_data["episodes"][0] == episode


class TestEpisodeDetail:
    def test_anonymous(self, rf, episode, anonymous_user):
        req = rf.get(episode.get_absolute_url())
        req.user = anonymous_user
        resp = views.episode_detail(req, episode.id, episode.slug)
        assert resp.status_code == 200
        assert resp.context_data["episode"] == episode
        assert not resp.context_data["is_bookmarked"]

    def test_user_not_bookmarked(self, rf, episode, user):
        req = rf.get(episode.get_absolute_url())
        req.user = user
        resp = views.episode_detail(req, episode.id, episode.slug)
        assert resp.status_code == 200
        assert resp.context_data["episode"] == episode
        assert not resp.context_data["is_bookmarked"]

    def test_user_bookmarked(self, rf, episode, user):
        BookmarkFactory(episode=episode, user=user)
        req = rf.get(episode.get_absolute_url())
        req.user = user
        resp = views.episode_detail(req, episode.id, episode.slug)
        assert resp.status_code == 200
        assert resp.context_data["episode"] == episode
        assert resp.context_data["is_bookmarked"]


class TestStartPlayer:
    def test_anonymous(self, rf, anonymous_user, episode):
        req = rf.post(reverse("episodes:start_player", args=[episode.id]))
        req.user = anonymous_user
        req.session = {}
        resp = views.start_player(req, episode.id)
        assert resp.status_code == 200
        assert req.session["player"] == {
            "episode": episode.id,
            "current_time": 0,
            "paused": False,
        }

    def test_authenticated(self, rf, user, episode):
        req = rf.post(reverse("episodes:start_player", args=[episode.id]))
        req.user = user
        req.session = {}
        resp = views.start_player(req, episode.id)
        assert resp.status_code == 200
        assert req.session["player"] == {
            "episode": episode.id,
            "current_time": 0,
            "paused": False,
        }


class TestStopPlayer:
    def test_anonymous(self, rf, anonymous_user, episode):
        req = rf.post(reverse("episodes:stop_player"))
        req.user = anonymous_user
        req.session = {"player": {"episode": episode.id, "current_time": 1000}}
        resp = views.stop_player(req)

        assert req.session == {}

        assert resp.status_code == 200
        body = json.loads(resp.content)
        assert body["current_time"] == 1000

    def test_authenticated(self, rf, user, episode):
        req = rf.post(
            reverse("episodes:stop_player"),
            data=json.dumps({"current_time": 1030}),
            content_type="application/json",
        )
        req.user = user
        req.session = {"player": {"episode": episode.id, "current_time": 1000}}

        resp = views.stop_player(req)

        assert req.session == {}

        assert resp.status_code == 200
        body = json.loads(resp.content)
        assert body["current_time"] == 1000

        log = AudioLog.objects.get(user=user, episode=episode)
        assert log.current_time == 1000


class TestUpdatePlayerTime:
    def test_anonymous(self, rf, anonymous_user, episode):
        req = rf.post(
            reverse("episodes:update_player_time"),
            data=json.dumps({"current_time": 1030}),
            content_type="application/json",
        )
        req.user = anonymous_user
        req.session = {"player": {"episode": episode.id, "current_time": 1000}}
        resp = views.update_player_time(req)
        assert req.session == {"player": {"episode": episode.id, "current_time": 1030}}

        assert resp.status_code == 200
        body = json.loads(resp.content)
        assert body["current_time"] == 1030

    def test_authenticated(self, rf, user, episode):
        req = rf.post(
            reverse("episodes:update_player_time"),
            data=json.dumps({"current_time": 1030}),
            content_type="application/json",
        )
        req.user = user
        req.session = {"player": {"episode": episode.id, "current_time": 1000}}

        resp = views.update_player_time(req)

        assert req.session == {"player": {"episode": episode.id, "current_time": 1030}}

        assert resp.status_code == 200
        body = json.loads(resp.content)
        assert body["current_time"] == 1030

        log = AudioLog.objects.get(user=user, episode=episode)
        assert log.current_time == 1030

    def test_player_not_running(self, rf, user, episode):
        req = rf.post(
            reverse("episodes:update_player_time"),
            data=json.dumps({"current_time": 1030}),
            content_type="application/json",
        )
        req.user = user
        req.session = {}

        resp = views.update_player_time(req)

        assert req.session == {}
        assert resp.status_code == 400
        assert AudioLog.objects.count() == 0


class TestHistory:
    def test_get(self, rf, user):
        AudioLogFactory.create_batch(3, user=user)
        req = rf.get(reverse("episodes:history"))
        req.user = user
        resp = views.history(req)
        assert resp.status_code == 200
        assert len(resp.context_data["logs"]) == 3

    def test_search(self, rf, user):

        for _ in range(3):
            AudioLogFactory(
                user=user, episode=EpisodeFactory(title="zzzz", keywords="zzzzz"),
            )

        AudioLogFactory(user=user, episode=EpisodeFactory(title="testing"))
        req = rf.get(reverse("episodes:history"), {"q": "testing"})
        req.user = user
        resp = views.history(req)
        assert resp.status_code == 200
        assert resp.context_data["search"] == "testing"
        assert len(resp.context_data["logs"]) == 1


class TestBookmarkList:
    def test_get(self, rf, user):
        BookmarkFactory.create_batch(3, user=user)
        req = rf.get(reverse("episodes:bookmark_list"))
        req.user = user
        resp = views.bookmark_list(req)
        assert resp.status_code == 200
        assert len(resp.context_data["bookmarks"]) == 3

    def test_search(self, rf, user):

        for _ in range(3):
            BookmarkFactory(
                user=user, episode=EpisodeFactory(title="zzzz", keywords="zzzzz")
            )

        BookmarkFactory(user=user, episode=EpisodeFactory(title="testing"))
        req = rf.get(reverse("episodes:bookmark_list"), {"q": "testing"})
        req.user = user
        resp = views.bookmark_list(req)
        assert resp.status_code == 200
        assert resp.context_data["search"] == "testing"
        assert len(resp.context_data["bookmarks"]) == 1


class TestAddBookmark:
    def test_post(self, rf, user, episode, mocker):
        req = rf.post(reverse("episodes:add_bookmark", args=[episode.id]))
        req.user = user
        req._messages = mocker.Mock()
        resp = views.add_bookmark(req, episode.id)
        assert resp.url == episode.get_absolute_url()
        assert Bookmark.objects.filter(user=user, episode=episode).exists()
        req._messages.add.assert_called()


class TestRemoveBookmark:
    def test_post(self, rf, user, episode, mocker):
        BookmarkFactory(user=user, episode=episode)
        req = rf.post(reverse("episodes:remove_bookmark", args=[episode.id]))
        req.user = user
        req._messages = mocker.Mock()
        resp = views.remove_bookmark(req, episode.id)
        assert resp.url == episode.get_absolute_url()
        assert not Bookmark.objects.filter(user=user, episode=episode).exists()
        req._messages.add.assert_called()
