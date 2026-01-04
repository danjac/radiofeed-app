import pytest
from django.urls import reverse, reverse_lazy
from pytest_django.asserts import assertContains, assertTemplateUsed

from simplecasts.models import Podcast
from simplecasts.tests.asserts import (
    assert200,
    assert404,
)
from simplecasts.tests.factories import (
    CategoryFactory,
    EpisodeFactory,
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)


class TestDiscover:
    url = reverse_lazy("podcasts:discover")

    @pytest.mark.django_db
    def test_get(self, client, auth_user, settings):
        settings.DISCOVER_FEED_LANGUAGE = "en"
        response = client.get(self.url)
        PodcastFactory.create_batch(3, promoted=True, language="en")
        assert200(response)
        assertTemplateUsed(response, "podcasts/discover.html")

    @pytest.mark.django_db
    def test_empty(self, client, auth_user):
        response = client.get(self.url)
        assert200(response)
        assertTemplateUsed(response, "podcasts/discover.html")

        assert len(response.context["podcasts"]) == 0


class TestPodcastSimilar:
    @pytest.mark.django_db
    def test_get(self, client, auth_user, podcast):
        EpisodeFactory.create_batch(3, podcast=podcast)
        RecommendationFactory.create_batch(3, podcast=podcast)
        response = client.get(podcast.get_similar_url())

        assert200(response)

        assert response.context["podcast"] == podcast
        assert len(response.context["recommendations"]) == 3


class TestPodcastDetail:
    @pytest.fixture
    def podcast(self, faker):
        return PodcastFactory(
            owner=faker.name(),
            website=faker.url(),
            funding_url=faker.url(),
            funding_text=faker.text(),
            categories=CategoryFactory.create_batch(3),
        )

    @pytest.mark.django_db
    def test_get_podcast_no_website(self, client, auth_user, faker):
        podcast = PodcastFactory(website="", owner=faker.name())
        response = client.get(podcast.get_absolute_url())

        assert200(response)

        assert response.context["podcast"] == podcast

    @pytest.mark.django_db
    def test_get_podcast_subscribed(self, client, auth_user, podcast):
        podcast.categories.set(CategoryFactory.create_batch(3))
        SubscriptionFactory(subscriber=auth_user, podcast=podcast)
        response = client.get(podcast.get_absolute_url())

        assert200(response)

        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is True

    @pytest.mark.django_db
    def test_get_podcast_private_subscribed(self, client, auth_user):
        podcast = PodcastFactory(private=True)
        SubscriptionFactory(subscriber=auth_user, podcast=podcast)
        response = client.get(podcast.get_absolute_url())

        assert200(response)

        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is True

    @pytest.mark.django_db
    def test_get_podcast_private_not_subscribed(self, client, auth_user):
        podcast = PodcastFactory(private=True)
        response = client.get(podcast.get_absolute_url())

        assert200(response)

        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is False

    @pytest.mark.django_db
    def test_get_podcast_not_subscribed(self, client, auth_user, podcast):
        response = client.get(podcast.get_absolute_url())

        assert200(response)

        assert response.context["podcast"] == podcast
        assert response.context["is_subscribed"] is False

    @pytest.mark.django_db
    def test_get_podcast_admin(self, client, staff_user, podcast):
        response = client.get(podcast.get_absolute_url())

        assert200(response)

        assert response.context["podcast"] == podcast
        assertContains(response, "Admin")

    @pytest.mark.django_db
    def test_redirect_to_canonical(self, client, auth_user, podcast):
        duplicate = PodcastFactory(canonical=podcast)
        response = client.get(duplicate.get_absolute_url())
        assert200(response)
        assertContains(response, "moved")


class TestLatestEpisode:
    @pytest.mark.django_db
    def test_ok(self, client, auth_user, episode):
        response = client.get(self.url(episode.podcast))
        assert response.url == episode.get_absolute_url()

    @pytest.mark.django_db
    def test_no_episodes(self, client, auth_user, podcast):
        response = client.get(self.url(podcast))
        assert404(response)

    def url(self, podcast):
        return reverse("podcasts:latest_episode", args=[podcast.pk])


class TestPodcastSeason:
    @pytest.mark.django_db
    def test_get_episodes_for_season(self, client, auth_user, podcast):
        EpisodeFactory.create_batch(20, podcast=podcast, season=1)
        EpisodeFactory.create_batch(10, podcast=podcast, season=2)

        response = client.get(
            reverse(
                "podcasts:season",
                kwargs={
                    "podcast_id": podcast.pk,
                    "slug": podcast.slug,
                    "season": 1,
                },
            )
        )
        assert200(response)

        assert len(response.context["page"].object_list) == 20
        assert response.context["season"].season == 1

    @pytest.mark.django_db
    def test_get_serial(self, client, auth_user):
        podcast = PodcastFactory(podcast_type=Podcast.PodcastType.SERIAL)
        EpisodeFactory.create_batch(20, podcast=podcast, season=1)
        EpisodeFactory.create_batch(10, podcast=podcast, season=2)

        response = client.get(
            reverse(
                "podcasts:season",
                kwargs={
                    "podcast_id": podcast.pk,
                    "slug": podcast.slug,
                    "season": 1,
                },
            )
        )
        assert200(response)

        assert len(response.context["page"].object_list) == 20
        assert response.context["season"].season == 1


class TestPodcastEpisodes:
    @pytest.mark.django_db
    def test_get_episodes(self, client, auth_user, podcast):
        EpisodeFactory.create_batch(33, podcast=podcast)

        response = client.get(podcast.get_episodes_url())
        assert200(response)

        assert len(response.context["page"].object_list) == 30
        assert response.context["ordering"] == "desc"

    @pytest.mark.django_db
    def test_serial(self, client, auth_user):
        podcast = PodcastFactory(podcast_type=Podcast.PodcastType.SERIAL)
        EpisodeFactory.create_batch(33, podcast=podcast)

        response = client.get(podcast.get_episodes_url())
        assert200(response)

        assert len(response.context["page"].object_list) == 30
        assert response.context["ordering"] == "asc"

    @pytest.mark.django_db
    def test_no_episodes(self, client, auth_user, podcast):
        response = client.get(podcast.get_episodes_url())

        assert200(response)
        assert len(response.context["page"].object_list) == 0

    @pytest.mark.django_db
    def test_ascending(self, client, auth_user, podcast):
        EpisodeFactory.create_batch(33, podcast=podcast)

        response = client.get(
            podcast.get_episodes_url(),
            {"order": "asc"},
        )
        assert200(response)

        assert len(response.context["page"].object_list) == 30

    @pytest.mark.django_db
    def test_search(self, client, auth_user, podcast, faker):
        EpisodeFactory.create_batch(3, podcast=podcast)

        episode = EpisodeFactory(title=faker.unique.name(), podcast=podcast)

        response = client.get(
            podcast.get_episodes_url(),
            {"search": episode.title},
        )
        assert200(response)
        assert len(response.context["page"].object_list) == 1
