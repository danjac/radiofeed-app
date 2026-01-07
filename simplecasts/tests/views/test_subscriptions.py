import pytest
from django.urls import reverse, reverse_lazy
from pytest_django.asserts import assertContains, assertTemplateUsed

from simplecasts.models import Subscription
from simplecasts.tests.asserts import assert200, assert404, assert409
from simplecasts.tests.factories import PodcastFactory, SubscriptionFactory


class TestSubscriptions:
    @pytest.mark.django_db
    def test_authenticated_no_subscriptions(self, client, auth_user):
        response = client.get(reverse("subscriptions:subscriptions"))
        assert200(response)

        assertTemplateUsed(response, "podcasts/subscriptions.html")

    @pytest.mark.django_db
    def test_user_is_subscribed(self, client, auth_user):
        """If user subscribed any podcasts, show only own feed with these podcasts"""

        sub = SubscriptionFactory(subscriber=auth_user)
        response = client.get(reverse("subscriptions:subscriptions"))

        assert200(response)

        assertTemplateUsed(response, "podcasts/subscriptions.html")

        assert len(response.context["page"].object_list) == 1
        assert response.context["page"].object_list[0] == sub.podcast

    @pytest.mark.django_db
    def test_htmx_request(self, client, auth_user):
        sub = SubscriptionFactory(subscriber=auth_user)
        response = client.get(
            reverse("subscriptions:subscriptions"),
            headers={
                "HX-Request": "true",
                "HX-Target": "pagination",
            },
        )

        assert200(response)

        assertContains(response, 'id="pagination"')

        assert len(response.context["page"].object_list) == 1
        assert response.context["page"].object_list[0] == sub.podcast

    @pytest.mark.django_db
    def test_user_is_subscribed_search(self, client, auth_user):
        """If user subscribed any podcasts, show only own feed with these podcasts"""

        sub = SubscriptionFactory(subscriber=auth_user)
        response = client.get(
            reverse("subscriptions:subscriptions"), {"search": sub.podcast.title}
        )

        assert200(response)

        assertTemplateUsed(response, "podcasts/subscriptions.html")

        assert len(response.context["page"].object_list) == 1
        assert response.context["page"].object_list[0] == sub.podcast


class TestSubscribe:
    @pytest.mark.django_db
    def test_subscribe(self, client, podcast, auth_user):
        response = client.post(
            self.url(podcast),
            headers={
                "HX-Request": "true",
            },
        )

        assert200(response)
        assertContains(response, 'id="subscribe-button"')

        assert Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()

    @pytest.mark.django_db(transaction=True)
    def test_already_subscribed(
        self,
        client,
        podcast,
        auth_user,
    ):
        SubscriptionFactory(subscriber=auth_user, podcast=podcast)
        response = client.post(
            self.url(podcast),
            headers={
                "HX-Request": "true",
                "HX-Target": "subscribe-button",
            },
        )

        assert409(response)

        assert Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()

    @pytest.mark.django_db
    def test_subscribe_private(self, client, auth_user):
        podcast = PodcastFactory(private=True)

        response = client.post(
            self.url(podcast),
            headers={
                "HX-Request": "true",
                "HX-Target": "subscribe-button",
            },
        )

        assert404(response)

        assert not Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()

    def url(self, podcast):
        return reverse("subscriptions:subscribe", args=[podcast.pk])


class TestUnsubscribe:
    @pytest.mark.django_db
    def test_unsubscribe(self, client, auth_user, podcast):
        SubscriptionFactory(subscriber=auth_user, podcast=podcast)
        response = client.delete(
            self.url(podcast),
            headers={
                "HX-Request": "true",
                "HX-Target": "subscribe-button",
            },
        )

        assert200(response)
        assertContains(response, 'id="subscribe-button"')

        assert not Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()

    @pytest.mark.django_db
    def test_unsubscribe_private(self, client, auth_user):
        podcast = SubscriptionFactory(
            subscriber=auth_user, podcast=PodcastFactory(private=True)
        ).podcast

        response = client.delete(
            self.url(podcast),
            headers={
                "HX-Request": "true",
                "HX-Target": "subscribe-button",
            },
        )

        assert404(response)

        assert Subscription.objects.filter(
            podcast=podcast, subscriber=auth_user
        ).exists()

    def url(self, podcast):
        return reverse("subscriptions:unsubscribe", args=[podcast.pk])
