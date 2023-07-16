from datetime import timedelta

import pytest
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from pytest_django.asserts import assertContains, assertNotContains

from radiofeed.episodes.middleware import Player
from radiofeed.episodes.models import AudioLog, Bookmark
from radiofeed.episodes.tests.factories import (
    create_audio_log,
    create_bookmark,
    create_episode,
)
from radiofeed.podcasts.tests.factories import create_podcast, create_subscription
from radiofeed.tests.asserts import (
    assert_bad_request,
    assert_conflict,
    assert_no_content,
    assert_not_found,
    assert_ok,
)
from radiofeed.tests.factories import create_batch

episodes_url = reverse_lazy("episodes:index")


@pytest.fixture()
def player_episode(auth_user, client, episode):
    create_audio_log(user=auth_user, episode=episode)

    session = client.session
    session[Player.session_key] = episode.id
    session.save()

    return episode


class TestNewEpisodes:
    @pytest.mark.django_db()
    def test_no_episodes(self, client, auth_user):
        response = client.get(episodes_url)
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 0

    @pytest.mark.django_db()
    def test_not_subscribed(self, client, auth_user):
        promoted = create_podcast(promoted=True)
        create_episode(podcast=promoted)
        create_batch(create_episode, 3)
        response = client.get(episodes_url)
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 1
        assert response.context["promoted"]
        assert not response.context["has_subscriptions"]

    @pytest.mark.django_db()
    def test_user_has_subscribed(self, client, auth_user):
        promoted = create_podcast(promoted=True)
        create_episode(podcast=promoted)

        create_batch(create_episode, 3)

        episode = create_episode()
        create_subscription(subscriber=auth_user, podcast=episode.podcast)

        response = client.get(episodes_url)
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 1
        assert response.context["page_obj"].object_list[0] == episode
        assert not response.context["promoted"]
        assert response.context["has_subscriptions"]

    @pytest.mark.django_db()
    def test_user_has_subscribed_promoted(self, client, auth_user):
        promoted = create_podcast(promoted=True)
        create_episode(podcast=promoted)

        create_batch(create_episode, 3)

        episode = create_episode()
        create_subscription(subscriber=auth_user, podcast=episode.podcast)

        response = client.get(episodes_url, {"promoted": True})

        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 1
        assert response.context["page_obj"].object_list[0].podcast == promoted
        assert response.context["promoted"]
        assert response.context["has_subscriptions"]


class TestSearchEpisodes:
    url = reverse_lazy("episodes:search_episodes")

    @pytest.mark.django_db()
    def test_no_results(self, auth_user, client):
        assert_ok(client.get(self.url, {"query": "test"}))

    @pytest.mark.django_db()
    def test_search_empty(self, auth_user, client):
        assert client.get(self.url, {"query": ""}).url == episodes_url

    @pytest.mark.django_db()
    def test_search(self, auth_user, client, faker):
        create_batch(create_episode, 3, title="zzzz", keywords="zzzz")
        episode = create_episode(title=faker.unique.name())
        response = client.get(self.url, {"query": episode.title})
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 1
        assert response.context["page_obj"].object_list[0] == episode

    @pytest.mark.django_db()
    def test_search_no_results(self, auth_user, client):
        response = client.get(self.url, {"query": "zzzz"})
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 0


class TestEpisodeDetail:
    @pytest.fixture()
    def episode(self, faker):
        return create_episode(
            podcast=create_podcast(
                owner=faker.name(),
                website=faker.url(),
                funding_url=faker.url(),
                funding_text=faker.text(),
                keywords=faker.text(),
                explicit=True,
            ),
            episode_type="full",
            season=1,
            episode=3,
            length=9000,
            duration="3:30:30",
        )

    @pytest.fixture()
    def prev_episode(self, auth_user, episode):
        return create_episode(
            podcast=episode.podcast, pub_date=episode.pub_date - timedelta(days=7)
        )

    @pytest.fixture()
    def next_episode(self, auth_user, episode):
        return create_episode(
            podcast=episode.podcast, pub_date=episode.pub_date + timedelta(days=7)
        )

    @pytest.mark.django_db()
    def test_ok(
        self,
        client,
        auth_user,
        episode,
        prev_episode,
        next_episode,
    ):
        response = client.get(episode.get_absolute_url())
        assert_ok(response)
        assert response.context["episode"] == episode

    @pytest.mark.django_db()
    def test_listened(
        self,
        client,
        auth_user,
        episode,
        prev_episode,
        next_episode,
    ):
        create_audio_log(
            episode=episode, user=auth_user, current_time=900, listened=timezone.now()
        )

        response = client.get(episode.get_absolute_url())
        assert_ok(response)

        assert response.context["episode"] == episode

        assertContains(response, "Remove episode from your History")
        assertContains(response, "Listened")

    @pytest.mark.django_db()
    def test_no_prev_next_episde(
        self,
        client,
        auth_user,
        episode,
    ):
        response = client.get(episode.get_absolute_url())
        assert_ok(response)
        assert response.context["episode"] == episode
        assertNotContains(response, "No More Episodes")

    @pytest.mark.django_db()
    def test_no_next_episode(
        self,
        client,
        auth_user,
        episode,
    ):
        create_episode(
            podcast=episode.podcast, pub_date=episode.pub_date - timedelta(days=30)
        )
        response = client.get(episode.get_absolute_url())
        assert_ok(response)
        assert response.context["episode"] == episode
        assertContains(response, "Last Episode")

    @pytest.mark.django_db()
    def test_no_previous_episode(
        self,
        client,
        auth_user,
        episode,
    ):
        create_episode(
            podcast=episode.podcast, pub_date=episode.pub_date + timedelta(days=30)
        )
        response = client.get(episode.get_absolute_url())
        assert_ok(response)
        assert response.context["episode"] == episode
        assertContains(response, "First Episode")


class TestStartPlayer:
    def url(self, episode):
        return reverse("episodes:start_player", args=[episode.id])

    @pytest.mark.django_db()
    def test_play_from_start(self, client, auth_user, episode):
        response = client.post(
            self.url(episode),
            HTTP_HX_REQUEST="true",
        )

        assert_ok(response)

        assert response.context["start_player"]
        assert response.context["is_playing"]

        assert AudioLog.objects.filter(user=auth_user, episode=episode).exists()

        assert client.session[Player.session_key] == episode.id

    @pytest.mark.django_db()
    def test_play_private_subscribed(self, client, auth_user):
        episode = create_episode(podcast=create_podcast(private=True))
        create_subscription(subscriber=auth_user, podcast=episode.podcast)
        assert_ok(
            client.post(
                self.url(episode),
                HTTP_HX_REQUEST="true",
            ),
        )

        assert AudioLog.objects.filter(user=auth_user, episode=episode).exists()

        assert client.session[Player.session_key] == episode.id

    @pytest.mark.django_db()
    def test_another_episode_in_player(self, client, auth_user, player_episode):
        episode = create_episode()

        assert_ok(
            client.post(
                self.url(episode),
                HTTP_HX_REQUEST="true",
            ),
        )

        assert AudioLog.objects.filter(user=auth_user, episode=episode).exists()

        assert client.session[Player.session_key] == episode.id

    @pytest.mark.django_db()
    def test_resume(self, client, auth_user, player_episode):
        assert_ok(
            client.post(
                self.url(player_episode),
                HTTP_HX_REQUEST="true",
            ),
        )

        assert client.session[Player.session_key] == player_episode.id


class TestClosePlayer:
    url = reverse_lazy("episodes:close_player")

    @pytest.mark.django_db()
    def test_player_empty(self, client, auth_user, episode):
        assert_no_content(client.post(self.url, HTTP_HX_REQUEST="true"))

    @pytest.mark.django_db()
    def test_close(
        self,
        client,
        player_episode,
    ):
        response = client.post(
            self.url,
            HTTP_HX_REQUEST="true",
        )

        assert_ok(response)

        assert not response.context["start_player"]
        assert not response.context["is_playing"]

        assert player_episode.id not in client.session


class TestPlayerTimeUpdate:
    url = reverse_lazy("episodes:player_time_update")

    @pytest.mark.django_db()
    def test_is_running(self, client, player_episode):
        assert_no_content(
            client.post(
                self.url,
                {"current_time": "1030"},
            )
        )

        log = AudioLog.objects.first()

        assert log.current_time == 1030

    @pytest.mark.django_db()
    def test_player_log_missing(self, client, auth_user, episode):
        session = client.session
        session[Player.session_key] = episode.id
        session.save()

        assert_no_content(
            client.post(
                self.url,
                {"current_time": "1030"},
            )
        )
        log = AudioLog.objects.first()

        assert log.current_time == 1030
        assert log.episode == episode

    @pytest.mark.django_db()
    def test_player_not_in_session(self, client, auth_user, episode):
        assert_no_content(
            client.post(
                self.url,
                {"current_time": "1030"},
            )
        )

        assert not AudioLog.objects.exists()

    @pytest.mark.django_db()
    def test_missing_data(self, client, auth_user, player_episode):
        assert_bad_request(client.post(self.url))

    @pytest.mark.django_db()
    def test_invalid_data(self, client, auth_user, player_episode):
        assert_bad_request(client.post(self.url, {"current_time": "xyz"}))


class TestBookmarks:
    url = reverse_lazy("episodes:bookmarks")

    @pytest.mark.django_db()
    def test_get(self, client, auth_user):
        create_batch(create_bookmark, 33, user=auth_user)

        response = client.get(self.url)

        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 30

    @pytest.mark.django_db()
    def test_ascending(self, client, auth_user):
        create_batch(create_bookmark, 33, user=auth_user)

        response = client.get(self.url, {"order": "asc"})

        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 30

    @pytest.mark.django_db()
    def test_empty(self, client, auth_user):
        response = client.get(self.url)

        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 0

    @pytest.mark.django_db()
    def test_search(self, client, auth_user):
        podcast = create_podcast(title="zzzz", keywords="zzzzz")

        for _ in range(3):
            create_bookmark(
                user=auth_user,
                episode=create_episode(title="zzzz", keywords="zzzzz", podcast=podcast),
            )

        create_bookmark(user=auth_user, episode=create_episode(title="testing"))

        response = client.get(self.url, {"query": "testing"})
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 1


class TestAddBookmark:
    def url(self, episode):
        return reverse("episodes:add_bookmark", args=[episode.id])

    @pytest.mark.django_db()
    def test_post(self, client, auth_user, episode):
        assert_ok(
            client.post(
                self.url(episode),
                HTTP_HX_REQUEST="true",
            )
        )
        assert Bookmark.objects.filter(user=auth_user, episode=episode).exists()

    @pytest.mark.django_db()(transaction=True)
    def test_already_bookmarked(self, client, auth_user, episode):
        create_bookmark(episode=episode, user=auth_user)
        assert_conflict(
            client.post(
                self.url(episode),
                HTTP_HX_REQUEST="true",
            )
        )
        assert Bookmark.objects.filter(user=auth_user, episode=episode).exists()


class TestRemoveBookmark:
    def url(self, episode):
        return reverse("episodes:remove_bookmark", args=[episode.id])

    @pytest.mark.django_db()
    def test_post(self, client, auth_user, episode):
        create_bookmark(user=auth_user, episode=episode)
        assert_ok(
            client.delete(
                self.url(episode),
                HTTP_HX_REQUEST="true",
            )
        )
        assert not Bookmark.objects.filter(user=auth_user, episode=episode).exists()


class TestHistory:
    url = reverse_lazy("episodes:history")

    @pytest.mark.django_db()
    def test_get(self, client, auth_user):
        create_batch(create_audio_log, 33, user=auth_user)
        response = client.get(self.url)
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 30

    @pytest.mark.django_db()
    def test_empty(self, client, auth_user):
        response = client.get(self.url)
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 0

    @pytest.mark.django_db()
    def test_ascending(self, client, auth_user):
        create_batch(create_audio_log, 33, user=auth_user)

        response = client.get(self.url, {"order": "asc"})
        assert_ok(response)

        assert len(response.context["page_obj"].object_list) == 30

    @pytest.mark.django_db()
    def test_search(self, client, auth_user):
        podcast = create_podcast(title="zzzz", keywords="zzzzz")

        for _ in range(3):
            create_audio_log(
                user=auth_user,
                episode=create_episode(title="zzzz", keywords="zzzzz", podcast=podcast),
            )

        create_audio_log(user=auth_user, episode=create_episode(title="testing"))
        response = client.get(self.url, {"query": "testing"})
        assert_ok(response)
        assert len(response.context["page_obj"].object_list) == 1


class TestRemoveAudioLog:
    def url(self, episode):
        return reverse("episodes:remove_audio_log", args=[episode.id])

    @pytest.mark.django_db()
    def test_ok(self, client, auth_user, episode):
        create_audio_log(user=auth_user, episode=episode)
        create_audio_log(user=auth_user)

        assert_ok(
            client.delete(
                self.url(episode),
                HTTP_HX_TARGET="audio-log",
                HTTP_HX_REQUEST="true",
            )
        )

        assert not AudioLog.objects.filter(user=auth_user, episode=episode).exists()
        assert AudioLog.objects.filter(user=auth_user).count() == 1

    @pytest.mark.django_db()
    def test_is_playing(self, client, auth_user, player_episode):
        """Do not remove log if episode is currently playing"""

        assert_not_found(
            client.delete(
                self.url(player_episode),
                HTTP_HX_TARGET="audio-log",
                HTTP_HX_REQUEST="true",
            ),
        )
        assert AudioLog.objects.filter(user=auth_user, episode=player_episode).exists()

    @pytest.mark.django_db()
    def test_none_remaining(self, client, auth_user, episode):
        log = create_audio_log(user=auth_user, episode=episode)

        assert_ok(
            client.delete(
                self.url(log.episode),
                HTTP_HX_TARGET="audio-log",
                HTTP_HX_REQUEST="true",
            ),
        )

        assert not AudioLog.objects.filter(user=auth_user, episode=episode).exists()
        assert AudioLog.objects.filter(user=auth_user).count() == 0
