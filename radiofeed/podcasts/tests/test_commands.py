import pytest
from django.core.management import call_command
from django.utils import timezone

from radiofeed.episodes.tests.factories import AudioLogFactory, BookmarkFactory
from radiofeed.podcasts import itunes
from radiofeed.podcasts.models import Podcast
from radiofeed.podcasts.tests.factories import (
    PodcastFactory,
    RecommendationFactory,
    SubscriptionFactory,
)
from radiofeed.users.tests.factories import EmailAddressFactory


class TestRemoveOldPodcasts:
    @pytest.mark.django_db
    def test_remove_old_podcast(self, mocker):
        PodcastFactory(
            pub_date=timezone.now() - timezone.timedelta(days=366),
        )
        mocker.patch("builtins.input", return_value="Y")
        call_command("delete_inactive_podcasts")
        assert not Podcast.objects.exists()

    @pytest.mark.django_db
    def test_noinput(self):
        PodcastFactory(
            pub_date=timezone.now() - timezone.timedelta(days=366),
        )
        call_command("delete_inactive_podcasts", noinput=True)
        assert not Podcast.objects.exists()

    @pytest.mark.django_db
    def test_cancel_command(self, mocker):
        PodcastFactory(
            pub_date=timezone.now() - timezone.timedelta(days=366),
        )
        mocker.patch("builtins.input", return_value="n")
        call_command("delete_inactive_podcasts")
        assert Podcast.objects.exists()

    @pytest.mark.django_db
    def test_remove_inactive_podcast(self):
        PodcastFactory(active=False, pub_date=None)
        call_command("delete_inactive_podcasts", noinput=True)
        assert not Podcast.objects.exists()

    @pytest.mark.django_db
    def test_active_podcast(self):
        PodcastFactory(
            pub_date=timezone.now() - timezone.timedelta(days=30),
        )
        call_command("delete_inactive_podcasts", noinput=True)
        assert Podcast.objects.exists()

    @pytest.mark.django_db
    def test_remove_subscribed_podcast(self):
        SubscriptionFactory(
            podcast__pub_date=timezone.now() - timezone.timedelta(days=366),
        )
        call_command("delete_inactive_podcasts", noinput=True)
        assert Podcast.objects.exists()

    @pytest.mark.django_db
    def test_remove_bookmarked_podcast(self):
        BookmarkFactory(
            episode__podcast__pub_date=timezone.now() - timezone.timedelta(days=366),
        )
        call_command("delete_inactive_podcasts", noinput=True)
        assert Podcast.objects.exists()

    @pytest.mark.django_db
    def test_remove_listened_podcast(self):
        AudioLogFactory(
            episode__podcast__pub_date=timezone.now() - timezone.timedelta(days=366),
        )
        call_command("delete_inactive_podcasts", noinput=True)
        assert Podcast.objects.exists()


class TestFetchTopItunes:
    @pytest.mark.django_db
    def test_ok(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.itunes.fetch_chart",
            return_value=[
                PodcastFactory(),
            ],
        )
        call_command("fetch_top_itunes", "gb")
        patched.assert_called()

    @pytest.mark.django_db
    def test_error(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.itunes.fetch_chart",
            side_effect=itunes.ItunesError("Error"),
        )
        call_command("fetch_top_itunes", "gb")
        patched.assert_called()


class TestCreateRecommendations:
    @pytest.mark.django_db
    def test_create_recommendations(self, mocker):
        patched = mocker.patch(
            "radiofeed.podcasts.recommender.recommend",
            return_value=[
                ("en", RecommendationFactory.create_batch(3)),
            ],
        )
        call_command("create_recommendations")
        patched.assert_called()


class TestSendRecommendationsEmails:
    @pytest.fixture
    def recipient(self):
        return EmailAddressFactory(
            verified=True,
            primary=True,
        )

    @pytest.mark.django_db(transaction=True)
    def test_has_recommendations(self, mailoutbox, recipient):
        subscription = SubscriptionFactory(subscriber=recipient.user)
        RecommendationFactory.create_batch(3, podcast=subscription.podcast)
        call_command("send_recommendations")
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [recipient.email]
        assert recipient.user.recommended_podcasts.count() == 3

    @pytest.mark.django_db(transaction=True)
    def test_has_no_recommendations(self, mailoutbox, recipient):
        call_command("send_recommendations")
        assert len(mailoutbox) == 0
        assert recipient.user.recommended_podcasts.count() == 0

    @pytest.mark.django_db(transaction=True)
    def test_exception_raised(self, mocker, mailoutbox, recipient):
        mocker.patch(
            "radiofeed.podcasts.management.commands.send_recommendations.send_notification_email",
            side_effect=Exception("Error"),
        )
        subscription = SubscriptionFactory(subscriber=recipient.user)
        RecommendationFactory.create_batch(3, podcast=subscription.podcast)
        call_command("send_recommendations")
        assert len(mailoutbox) == 0
        assert recipient.user.recommended_podcasts.count() == 0
