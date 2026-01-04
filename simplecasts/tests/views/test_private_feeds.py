import pytest
from django.urls import reverse, reverse_lazy
from pytest_django.asserts import assertTemplateUsed

from simplecasts.models import Podcast, Subscription
from simplecasts.tests.asserts import (
    assert200,
    assert404,
)
from simplecasts.tests.factories import PodcastFactory, SubscriptionFactory


class TestPrivateFeeds:
    url = reverse_lazy("private_feeds:index")

    @pytest.mark.django_db
    def test_ok(self, client, auth_user):
        for podcast in PodcastFactory.create_batch(33, private=True):
            SubscriptionFactory(subscriber=auth_user, podcast=podcast)
        response = client.get(self.url)
        assert200(response)
        assert len(response.context["page"]) == 30
        assert response.context["page"].has_other_pages is True

    @pytest.mark.django_db
    def test_empty(self, client, auth_user):
        PodcastFactory(private=True)
        response = client.get(self.url)
        assert200(response)
        assert len(response.context["page"]) == 0
        assert response.context["page"].has_other_pages is False

    @pytest.mark.django_db
    def test_search(self, client, auth_user, faker):
        podcast = SubscriptionFactory(
            subscriber=auth_user,
            podcast=PodcastFactory(title=faker.unique.text(), private=True),
        ).podcast

        SubscriptionFactory(
            subscriber=auth_user,
            podcast=PodcastFactory(title="zzz", private=True),
        )

        response = client.get(self.url, {"search": podcast.title})
        assert200(response)

        assert len(response.context["page"].object_list) == 1
        assert response.context["page"].object_list[0] == podcast


class TestRemovePrivateFeed:
    def url(self, podcast):
        return reverse("private_feeds:remove", args=[podcast.pk])

    @pytest.mark.django_db
    def test_ok(self, client, auth_user):
        podcast = PodcastFactory(private=True)
        SubscriptionFactory(podcast=podcast, subscriber=auth_user)

        response = client.delete(
            self.url(podcast),
            {"rss": podcast.rss},
        )
        assert response.url == reverse("private_feeds:index")

        assert not Podcast.objects.filter(pk=podcast.pk).exists()

    @pytest.mark.django_db
    def test_not_owned_by_user(self, client, auth_user):
        podcast = PodcastFactory(private=True)

        response = client.delete(
            self.url(podcast),
            {"rss": podcast.rss},
        )
        assert404(response)

        assert Podcast.objects.filter(pk=podcast.pk).exists()

    @pytest.mark.django_db
    def test_not_private_feed(self, client, auth_user):
        podcast = PodcastFactory(private=False)
        SubscriptionFactory(podcast=podcast, subscriber=auth_user)
        response = client.delete(self.url(podcast), {"rss": podcast.rss})
        assert404(response)

        assert Podcast.objects.filter(pk=podcast.pk).exists()

        assert Subscription.objects.filter(
            subscriber=auth_user, podcast=podcast
        ).exists()


class TestAddPrivateFeed:
    url = reverse_lazy("private_feeds:add")

    @pytest.fixture
    def rss(self, faker):
        return faker.url()

    @pytest.mark.django_db
    def test_get(self, client, auth_user):
        response = client.get(self.url)
        assert200(response)
        assertTemplateUsed(response, "private_feeds/private_feed_form.html")

    @pytest.mark.django_db
    def test_post_not_existing(self, client, auth_user, rss):
        response = client.post(self.url, {"rss": rss})
        assert response.url == reverse("private_feeds:index")

        podcast = Subscription.objects.get(
            subscriber=auth_user, podcast__rss=rss
        ).podcast

        assert podcast.private

    @pytest.mark.django_db
    def test_existing_private(self, client, auth_user):
        podcast = PodcastFactory(private=True)

        response = client.post(self.url, {"rss": podcast.rss})
        assert200(response)

        assert not Subscription.objects.filter(
            subscriber=auth_user, podcast=podcast
        ).exists()

    @pytest.mark.django_db
    def test_existing_public(self, client, auth_user):
        podcast = PodcastFactory(private=False)

        response = client.post(self.url, {"rss": podcast.rss})
        assert200(response)

        assert not Subscription.objects.filter(
            subscriber=auth_user, podcast=podcast
        ).exists()
