import pytest
from django.utils import timezone

from radiofeed.podcasts.forms import PrivateFeedForm
from radiofeed.podcasts.models import Subscription
from radiofeed.podcasts.tests.factories import PodcastFactory, SubscriptionFactory


class TestPrivateFeedForm:
    rss = "https://example.com/rss"

    @pytest.mark.django_db
    def test_new_feed(self, user):
        form = PrivateFeedForm(data={"rss": self.rss}, user=user)
        assert form.is_valid()

        podcast, is_new = form.save()
        assert is_new is True
        assert podcast.private
        assert podcast.rss == self.rss

        assert Subscription.objects.filter(podcast=podcast, subscriber=user).exists()

    @pytest.mark.django_db
    def test_feed_exists(self, user):
        PodcastFactory(private=True, rss=self.rss, pub_date=timezone.now())
        form = PrivateFeedForm(data={"rss": self.rss}, user=user)
        assert form.is_valid()

        podcast, is_new = form.save()
        assert podcast.private
        assert is_new is False
        assert podcast.rss == self.rss

        assert Subscription.objects.filter(podcast=podcast, subscriber=user).exists()

    @pytest.mark.django_db
    def test_feed_exists_no_pub_date(self, user):
        PodcastFactory(private=True, rss=self.rss, pub_date=None)
        form = PrivateFeedForm(data={"rss": self.rss}, user=user)
        assert form.is_valid()

        podcast, is_new = form.save()
        assert podcast.private
        assert is_new is True
        assert podcast.rss == self.rss

        assert Subscription.objects.filter(podcast=podcast, subscriber=user).exists()

    @pytest.mark.django_db
    def test_feed_not_private(self, user):
        PodcastFactory(private=False, rss=self.rss)
        form = PrivateFeedForm(data={"rss": self.rss}, user=user)
        assert not form.is_valid()

    @pytest.mark.django_db
    def test_same_user_subscribed(self):
        user = SubscriptionFactory(
            podcast=PodcastFactory(private=True, rss=self.rss)
        ).subscriber
        form = PrivateFeedForm(data={"rss": self.rss}, user=user)
        assert not form.is_valid()

    @pytest.mark.django_db
    def test_other_user_subscribed(self, user):
        SubscriptionFactory(podcast=PodcastFactory(private=True, rss=self.rss))
        form = PrivateFeedForm(data={"rss": self.rss}, user=user)
        assert not form.is_valid()
