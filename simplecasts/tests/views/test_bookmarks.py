import pytest
from django.urls import reverse, reverse_lazy
from pytest_django.asserts import assertTemplateUsed

from simplecasts.models import Bookmark
from simplecasts.tests.asserts import (
    assert200,
    assert409,
)
from simplecasts.tests.factories import (
    BookmarkFactory,
    EpisodeFactory,
    PodcastFactory,
)


class TestBookmarks:
    url = reverse_lazy("episodes:bookmarks")

    @pytest.mark.django_db
    def test_get(self, client, auth_user):
        BookmarkFactory.create_batch(33, user=auth_user)

        response = client.get(self.url)

        assert200(response)
        assertTemplateUsed(response, "episodes/bookmarks.html")

        assert len(response.context["page"].object_list) == 30

    @pytest.mark.django_db
    def test_ascending(self, client, auth_user):
        BookmarkFactory.create_batch(33, user=auth_user)

        response = client.get(self.url, {"order": "asc"})

        assert200(response)
        assert len(response.context["page"].object_list) == 30

    @pytest.mark.django_db
    def test_empty(self, client, auth_user):
        response = client.get(self.url)
        assert200(response)

    @pytest.mark.django_db
    def test_search(self, client, auth_user):
        podcast = PodcastFactory(title="zzzz")

        for _ in range(3):
            BookmarkFactory(
                user=auth_user,
                episode=EpisodeFactory(title="zzzz", podcast=podcast),
            )

        BookmarkFactory(user=auth_user, episode=EpisodeFactory(title="testing"))

        response = client.get(self.url, {"search": "testing"})

        assert200(response)
        assertTemplateUsed(response, "episodes/bookmarks.html")

        assert len(response.context["page"].object_list) == 1


class TestAddBookmark:
    @pytest.mark.django_db
    def test_post(self, client, auth_user, episode):
        response = client.post(self.url(episode), headers={"HX-Request": "true"})

        assert200(response)
        assert Bookmark.objects.filter(user=auth_user, episode=episode).exists()

    @pytest.mark.django_db()(transaction=True)
    def test_already_bookmarked(self, client, auth_user, episode):
        BookmarkFactory(episode=episode, user=auth_user)

        response = client.post(self.url(episode), headers={"HX-Request": "true"})
        assert409(response)

        assert Bookmark.objects.filter(user=auth_user, episode=episode).exists()

    def url(self, episode):
        return reverse("episodes:add_bookmark", args=[episode.pk])


class TestRemoveBookmark:
    @pytest.mark.django_db
    def test_post(self, client, auth_user, episode):
        BookmarkFactory(user=auth_user, episode=episode)
        response = client.delete(
            reverse("episodes:remove_bookmark", args=[episode.pk]),
            headers={"HX-Request": "true"},
        )
        assert200(response)

        assert not Bookmark.objects.filter(user=auth_user, episode=episode).exists()
