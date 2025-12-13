import pytest

from listenwave.audio_player.middleware import PlayerDetails
from listenwave.episodes.tests.factories import (
    AudioLogFactory,
)


@pytest.fixture
def player_episode(auth_user, client, episode):
    AudioLogFactory(user=auth_user, episode=episode)

    session = client.session
    session[PlayerDetails.session_id] = episode.pk
    session.save()

    return episode
