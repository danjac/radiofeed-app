# Standard Library
import http
import json

# Django
from django.urls import reverse

# Third Party Libraries
import pytest

# RadioFeed
from radiofeed.podcasts.factories import PodcastFactory, SubscriptionFactory
from radiofeed.users.factories import UserFactory

# Local
from .. import views
from ..factories import AudioLogFactory, BookmarkFactory, EpisodeFactory
from ..models import AudioLog, Bookmark
from ..player import Player

pytestmark = pytest.mark.django_db


class TestEpisodeList:
    def test_anonymous(self, rf, anonymous_user):
        EpisodeFactory.create_batch(3)
        req = rf.get(reverse("episodes:episode_list"))
        req.user = anonymous_user
        resp = views.episode_list(req)
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 0

    def test_user_no_subscriptions(self, rf, user):
        EpisodeFactory.create_batch(3)
        req = rf.get(reverse("episodes:episode_list"))
        req.user = user
        resp = views.episode_list(req)
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 0

    def test_user_has_subscriptions(self, rf, user):
        EpisodeFactory.create_batch(3)

        episode = EpisodeFactory()
        SubscriptionFactory(user=user, podcast=episode.podcast)

        req = rf.get(reverse("episodes:episode_list"))
        req.user = user
        resp = views.episode_list(req)

        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == episode

    def test_anonymous_search(self, rf, anonymous_user):
        EpisodeFactory.create_batch(3, title="zzzz", keywords="zzzz")
        episode = EpisodeFactory(title="testing")
        req = rf.get(reverse("episodes:episode_list"), {"q": "testing"})
        req.user = anonymous_user
        resp = views.episode_list(req)
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == episode

    def test_user_has_subscriptions_search(self, rf, user):
        "Ignore subs in search"
        EpisodeFactory.create_batch(3, title="zzzz", keywords="zzzz")
        SubscriptionFactory(
            user=user, podcast=EpisodeFactory(title="zzzz", keywords="zzzz").podcast
        )
        episode = EpisodeFactory(title="testing")
        req = rf.get(reverse("episodes:episode_list"), {"q": "testing"})
        req.user = user
        resp = views.episode_list(req)
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 1
        assert resp.context_data["page_obj"].object_list[0] == episode


class TestBookmarkDetail:
    def test_anonymous(self, rf, bookmark, anonymous_user):
        req = rf.get(bookmark.get_absolute_url())
        req.user = anonymous_user
        resp = views.bookmark_detail(req, bookmark.episode.id, bookmark.episode.slug)
        assert resp.url == bookmark.episode.get_absolute_url()

    def test_authenticated(self, rf, bookmark, site):
        req = rf.get(bookmark.get_absolute_url())
        req.site = site
        req.user = bookmark.user
        resp = views.bookmark_detail(req, bookmark.episode.id, bookmark.episode.slug)
        assert resp.status_code == http.HTTPStatus.OK

    def test_not_user(self, rf, bookmark, site):
        req = rf.get(bookmark.get_absolute_url())
        req.site = site
        req.user = UserFactory()
        resp = views.bookmark_detail(req, bookmark.episode.id, bookmark.episode.slug)
        assert resp.url == bookmark.episode.get_absolute_url()


class TestHistoryDetail:
    def test_anonymous(self, rf, log, anonymous_user):
        req = rf.get(log.get_absolute_url())
        req.user = anonymous_user
        resp = views.history_detail(req, log.episode.id, log.episode.slug)
        assert resp.url == log.episode.get_absolute_url()

    def test_authenticated(self, rf, log, site):
        req = rf.get(log.get_absolute_url())
        req.site = site
        req.user = log.user
        resp = views.history_detail(req, log.episode.id, log.episode.slug)
        assert resp.status_code == http.HTTPStatus.OK

    def test_not_user(self, rf, log, site):
        req = rf.get(log.get_absolute_url())
        req.site = site
        req.user = UserFactory()
        resp = views.history_detail(req, log.episode.id, log.episode.slug)
        assert resp.url == log.episode.get_absolute_url()


class TestEpisodeDetail:
    def test_anonymous(self, rf, episode, anonymous_user, site):
        req = rf.get(episode.get_absolute_url())
        req.user = anonymous_user
        req.site = site
        resp = views.episode_detail(req, episode.id, episode.slug)
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["episode"] == episode
        assert not resp.context_data["is_bookmarked"]

    def test_user_not_bookmarked(self, rf, episode, user, site):
        req = rf.get(episode.get_absolute_url())
        req.user = user
        req.site = site
        resp = views.episode_detail(req, episode.id, episode.slug)
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["episode"] == episode
        assert not resp.context_data["is_bookmarked"]

    def test_user_bookmarked(self, rf, episode, user, site):
        BookmarkFactory(episode=episode, user=user)
        req = rf.get(episode.get_absolute_url())
        req.user = user
        req.site = site
        resp = views.episode_detail(req, episode.id, episode.slug)
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["episode"] == episode
        assert resp.context_data["is_bookmarked"]


class TestTogglePlayer:
    def test_anonymous(self, rf, anonymous_user, episode, mock_session):
        req = rf.post(reverse("episodes:toggle_player", args=[episode.id]))
        req.user = anonymous_user
        req.session = {}
        req.player = Player(req)
        resp = views.toggle_player(req, episode.id)
        assert resp.status_code == http.HTTPStatus.OK

        header = json.loads(resp["X-Player"])
        assert header["episode"] == episode.id
        assert header["action"] == "start"
        assert header["currentTime"] == 0
        assert header["mediaUrl"] == episode.media_url

        assert req.session["player"] == {
            "episode": episode.id,
            "current_time": 0,
        }

    def test_authenticated(self, rf, user, episode, mock_session):
        req = rf.post(reverse("episodes:toggle_player", args=[episode.id]))
        req.user = user
        req.session = mock_session()
        req.player = Player(req)
        resp = views.toggle_player(req, episode.id)
        assert resp.status_code == http.HTTPStatus.OK

        header = json.loads(resp["X-Player"])
        assert header["episode"] == episode.id
        assert header["action"] == "start"
        assert header["currentTime"] == 0
        assert header["mediaUrl"] == episode.media_url

        assert req.session["player"] == {
            "episode": episode.id,
            "current_time": 0,
        }

    def test_is_played(self, rf, user, episode, mock_session):
        AudioLogFactory(user=user, episode=episode, current_time=2000)
        req = rf.post(reverse("episodes:toggle_player", args=[episode.id]))
        req.user = user
        req.session = mock_session()
        req.player = Player(req)
        resp = views.toggle_player(req, episode.id)

        assert resp.status_code == http.HTTPStatus.OK

        header = json.loads(resp["X-Player"])
        assert header["episode"] == episode.id
        assert header["action"] == "start"
        assert header["currentTime"] == 2000
        assert header["mediaUrl"] == episode.media_url

        assert req.session["player"] == {
            "episode": episode.id,
            "current_time": 2000,
        }

    def test_stop(self, rf, user, episode, mock_session):
        AudioLogFactory(user=user, episode=episode, current_time=2000)
        req = rf.post(
            reverse("episodes:toggle_player", args=[episode.id]),
            {"player_action": "stop"},
        )
        req.user = user
        req.session = mock_session(
            {
                "player": {
                    "episode": episode.id,
                    "current_time": 0,
                }
            }
        )
        req.player = Player(req)
        resp = views.toggle_player(req, episode.id)
        assert resp.status_code == http.HTTPStatus.OK

        header = json.loads(resp["X-Player"])
        assert header["episode"] == episode.id
        assert header["action"] == "stop"


class TestMarkComplete:
    def test_anonymous(self, rf, anonymous_user, episode, mock_session):
        req = rf.post(reverse("episodes:mark_complete"))
        req.user = anonymous_user
        req.session = mock_session(
            {"player": {"episode": episode.id, "current_time": 1000}}
        )
        req.player = Player(req)
        resp = views.mark_complete(req)

        assert not req.player

        assert resp.status_code == http.HTTPStatus.NO_CONTENT

    def test_authenticated(self, rf, user, episode, mock_session):
        req = rf.post(
            reverse("episodes:mark_complete"),
            data=json.dumps({"currentTime": 1030}),
            content_type="application/json",
        )
        req.user = user
        req.session = mock_session(
            {"player": {"episode": episode.id, "current_time": 1000}}
        )
        req.player = Player(req)

        resp = views.mark_complete(req)

        assert not req.player

        assert resp.status_code == http.HTTPStatus.NO_CONTENT

        log = AudioLog.objects.get(user=user, episode=episode)
        assert log.current_time == 0
        assert log.completed


class TestPlayerTimeUpdate:
    def test_anonymous(self, rf, anonymous_user, episode, mock_session):
        req = rf.post(
            reverse("episodes:player_timeupdate"),
            data=json.dumps({"currentTime": 1030}),
            content_type="application/json",
        )
        req.user = anonymous_user
        req.session = mock_session(
            {"player": {"episode": episode.id, "current_time": 1000}}
        )
        req.player = Player(req)
        resp = views.player_timeupdate(req)
        assert req.session == {"player": {"episode": episode.id, "current_time": 1030}}

        assert resp.status_code == http.HTTPStatus.NO_CONTENT

    def test_authenticated(self, rf, user, episode, mock_session):
        req = rf.post(
            reverse("episodes:player_timeupdate"),
            data=json.dumps({"currentTime": 1030}),
            content_type="application/json",
        )
        req.user = user
        req.session = mock_session(
            {"player": {"episode": episode.id, "current_time": 1000}}
        )
        req.player = Player(req)

        resp = views.player_timeupdate(req)

        assert req.session == {"player": {"episode": episode.id, "current_time": 1030}}
        assert resp.status_code == http.HTTPStatus.NO_CONTENT

        log = AudioLog.objects.get(user=user, episode=episode)
        assert log.current_time == 1030

    def test_player_not_running(self, rf, user, episode):
        req = rf.post(
            reverse("episodes:player_timeupdate"),
            data=json.dumps({"current_time": 1030}),
            content_type="application/json",
        )
        req.user = user
        req.session = {}
        req.player = Player(req)

        resp = views.player_timeupdate(req)

        assert not req.player
        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
        assert AudioLog.objects.count() == 0

    def test_invalid_data(self, rf, user, episode, mock_session):
        req = rf.post(
            reverse("episodes:player_timeupdate"),
            data=json.dumps({}),
            content_type="application/json",
        )
        req.user = user
        req.session = mock_session(
            {"player": {"episode": episode.id, "current_time": 1030}}
        )
        req.player = Player(req)

        resp = views.player_timeupdate(req)

        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
        assert AudioLog.objects.count() == 0


class TestHistory:
    def test_get(self, rf, user):
        AudioLogFactory.create_batch(3, user=user)
        req = rf.get(reverse("episodes:history"))
        req.user = user
        resp = views.history(req)
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_search(self, rf, user):

        podcast = PodcastFactory(title="zzzz", keywords="zzzzz")

        for _ in range(3):
            AudioLogFactory(
                user=user,
                episode=EpisodeFactory(title="zzzz", keywords="zzzzz", podcast=podcast),
            )

        AudioLogFactory(user=user, episode=EpisodeFactory(title="testing"))
        req = rf.get(reverse("episodes:history"), {"q": "testing"})
        req.user = user
        resp = views.history(req)
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["search"] == "testing"
        assert len(resp.context_data["page_obj"].object_list) == 1


class TestBookmarkList:
    def test_get(self, rf, user):
        BookmarkFactory.create_batch(3, user=user)
        req = rf.get(reverse("episodes:bookmark_list"))
        req.user = user
        resp = views.bookmark_list(req)
        assert resp.status_code == http.HTTPStatus.OK
        assert len(resp.context_data["page_obj"].object_list) == 3

    def test_search(self, rf, user):

        podcast = PodcastFactory(title="zzzz", keywords="zzzzz")

        for _ in range(3):
            BookmarkFactory(
                user=user,
                episode=EpisodeFactory(title="zzzz", keywords="zzzzz", podcast=podcast),
            )

        BookmarkFactory(user=user, episode=EpisodeFactory(title="testing"))
        req = rf.get(reverse("episodes:bookmark_list"), {"q": "testing"})
        req.user = user
        resp = views.bookmark_list(req)
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.context_data["search"] == "testing"
        assert len(resp.context_data["page_obj"].object_list) == 1


class TestAddBookmark:
    def test_post(self, rf, user, episode):
        req = rf.post(reverse("episodes:add_bookmark", args=[episode.id]))
        req.user = user
        req.accept_turbo_stream = True
        resp = views.add_bookmark(req, episode.id)
        assert resp.status_code == http.HTTPStatus.OK
        assert Bookmark.objects.filter(user=user, episode=episode).exists()


class TestRemoveBookmark:
    def test_post(self, rf, user, episode):
        BookmarkFactory(user=user, episode=episode)
        req = rf.post(reverse("episodes:remove_bookmark", args=[episode.id]))
        req.user = user
        req.accept_turbo_stream = True
        resp = views.remove_bookmark(req, episode.id)
        assert resp.status_code == http.HTTPStatus.OK
        assert not Bookmark.objects.filter(user=user, episode=episode).exists()


class TestRemoveHistory:
    def test_post_one_remaining(self, rf, user, episode):
        AudioLogFactory(user=user, episode=episode)
        AudioLogFactory(user=user)
        req = rf.post(reverse("episodes:remove_history", args=[episode.id]))
        req.accept_turbo_stream = True
        req.user = user
        resp = views.remove_history(req, episode.id)
        assert resp.status_code == http.HTTPStatus.OK
        assert not AudioLog.objects.filter(user=user, episode=episode).exists()
        assert AudioLog.objects.filter(user=user).count() == 1

    def test_post_none_remaining(self, rf, user, episode, mocker):
        AudioLogFactory(user=user, episode=episode)
        req = rf.post(reverse("episodes:remove_history", args=[episode.id]))
        req.accept_turbo_stream = True
        req.user = user
        req._messages = mocker.Mock()
        resp = views.remove_history(req, episode.id)
        assert resp.url == reverse("episodes:history")
        assert not AudioLog.objects.filter(user=user, episode=episode).exists()
