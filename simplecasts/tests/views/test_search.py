import pytest
from django.urls import reverse, reverse_lazy
from pytest_django.asserts import assertContains, assertTemplateUsed

from simplecasts.services import itunes
from simplecasts.tests.asserts import (
    assert200,
)
from simplecasts.tests.factories import (
    EpisodeFactory,
    PodcastFactory,
)

_index_url = reverse_lazy("episodes:index")
_discover_url = reverse_lazy("podcasts:discover")


class TestSearchPeople:
    @pytest.mark.django_db
    def test_get(self, client, auth_user, faker):
        podcast = PodcastFactory(owner=faker.name())
        response = client.get(
            reverse("search:people"),
            {
                "search": podcast.cleaned_owner,
            },
        )
        assert200(response)
        assertTemplateUsed(response, "search/search_people.html")

    @pytest.mark.django_db
    def test_empty(self, client, auth_user):
        response = client.get(reverse("search:people"), {"search": ""})
        assert response.url == _discover_url


class TestSearchPodcasts:
    url = reverse_lazy("search:podcasts")

    @pytest.mark.django_db
    def test_search(self, client, auth_user, faker):
        podcast = PodcastFactory(title=faker.unique.text())
        PodcastFactory.create_batch(3, title="zzz")
        response = client.get(self.url, {"search": podcast.title})

        assert200(response)

        assert len(response.context["page"].object_list) == 1
        assert response.context["page"].object_list[0] == podcast

    @pytest.mark.django_db
    def test_search_value_empty(self, client, auth_user, faker):
        response = client.get(self.url, {"search": ""})
        assert response.url == _discover_url

    @pytest.mark.django_db
    def test_search_filter_private(self, client, auth_user, faker):
        podcast = PodcastFactory(title=faker.unique.text(), private=True)
        PodcastFactory.create_batch(3, title="zzz")
        response = client.get(self.url, {"search": podcast.title})

        assert200(response)

        assert len(response.context["page"].object_list) == 0

    @pytest.mark.django_db
    def test_search_no_results(self, client, auth_user, faker):
        response = client.get(self.url, {"search": "zzzz"})
        assert200(response)
        assert len(response.context["page"].object_list) == 0


class TestSearchItunes:
    url = reverse_lazy("search:itunes")

    @pytest.mark.django_db
    def test_empty(self, client, auth_user):
        response = client.get(self.url, {"search": ""})
        assert response.url == _discover_url

    @pytest.mark.django_db
    def test_search(self, client, auth_user, podcast, mocker):
        feeds = [
            itunes.Feed(
                artworkUrl100="https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3",
                collectionName="Test & Code : Python Testing",
                collectionViewUrl="https://example.com/id123456",
                feedUrl="https://feeds.fireside.fm/testandcode/rss",
            ),
            itunes.Feed(
                artworkUrl100="https://assets.fireside.fm/file/fireside-images/podcasts/images/b/bc7f1faf-8aad-4135-bb12-83a8af679756/cover.jpg?v=3",
                collectionName=podcast.title,
                collectionViewUrl=podcast.website,
                feedUrl=podcast.rss,
            ),
        ]
        mock_search = mocker.patch(
            "simplecasts.services.itunes.search_cached",
            return_value=(feeds, True),
        )

        response = client.get(self.url, {"search": "test"})
        assert200(response)

        assertTemplateUsed(response, "search/search_itunes.html")

        assertContains(response, "Test &amp; Code : Python Testing")
        assertContains(response, podcast.title)

        mock_search.assert_called()

    @pytest.mark.django_db
    def test_search_error(self, client, auth_user, mocker):
        mocker.patch(
            "simplecasts.services.itunes.search_cached",
            side_effect=itunes.ItunesError("Error"),
        )
        response = client.get(self.url, {"search": "test"})
        assert response.url == _discover_url


class TestSearchEpisodes:
    url = reverse_lazy("search:episodes")

    @pytest.mark.django_db
    def test_search(self, auth_user, client, faker):
        EpisodeFactory.create_batch(3, title="zzzz")
        episode = EpisodeFactory(title=faker.unique.name())
        response = client.get(self.url, {"search": episode.title})
        assert200(response)
        assertTemplateUsed(response, "search/search_episodes.html")
        assert len(response.context["page"].object_list) == 1
        assert response.context["page"].object_list[0] == episode

    @pytest.mark.django_db
    def test_search_no_results(self, auth_user, client):
        response = client.get(self.url, {"search": "zzzz"})
        assert200(response)
        assertTemplateUsed(response, "search/search_episodes.html")
        assert len(response.context["page"].object_list) == 0

    @pytest.mark.django_db
    def test_search_value_empty(self, auth_user, client):
        response = client.get(self.url, {"search": ""})
        assert response.url == _index_url
