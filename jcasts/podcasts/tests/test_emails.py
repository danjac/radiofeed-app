from jcasts.episodes.factories import AudioLogFactory, BookmarkFactory, EpisodeFactory
from jcasts.podcasts.emails import send_recommendations_email
from jcasts.podcasts.factories import FollowFactory, RecommendationFactory


class TestSendRecommendationEmail:
    def test_send_if_no_recommendations_or_episodes(self, user, mailoutbox):
        """If no recommendations, don't send."""

        send_recommendations_email(user)
        assert len(mailoutbox) == 0

    def test_send_if_sufficient_episodes(self, user, mailoutbox):

        first = FollowFactory(user=user).podcast
        second = FollowFactory(user=user).podcast
        third = FollowFactory(user=user).podcast

        EpisodeFactory()

        first_episode = EpisodeFactory(podcast=first)
        second_episode = EpisodeFactory(podcast=third)

        EpisodeFactory(podcast=first)

        AudioLogFactory(user=user, episode=first_episode)
        BookmarkFactory(user=user, episode=second_episode)

        EpisodeFactory(podcast=first)
        EpisodeFactory(podcast=second)
        EpisodeFactory(podcast=third)

        send_recommendations_email(user)

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [user.email]

    def test_send_if_sufficient_recommendations(self, user, mailoutbox):

        first = FollowFactory(user=user).podcast
        second = FollowFactory(user=user).podcast
        third = FollowFactory(user=user).podcast

        RecommendationFactory(podcast=first)
        RecommendationFactory(podcast=second)
        RecommendationFactory(podcast=third)

        send_recommendations_email(user)

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [user.email]
        assert user.recommended_podcasts.count() == 3

    def test_send_if_sufficient_recommendations_and_episodes(self, user, mailoutbox):

        first = FollowFactory(user=user).podcast
        second = FollowFactory(user=user).podcast
        third = FollowFactory(user=user).podcast

        RecommendationFactory(podcast=first)
        RecommendationFactory(podcast=second)
        RecommendationFactory(podcast=third)

        EpisodeFactory(podcast=first)
        EpisodeFactory(podcast=second)
        EpisodeFactory(podcast=third)

        send_recommendations_email(user)

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [user.email]
        assert user.recommended_podcasts.count() == 3
