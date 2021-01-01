# Third Party Libraries
import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator

# Local
from ..consumers import PlayerConsumer
from ..factories import EpisodeFactory

pytestmark = pytest.mark.django_db


@database_sync_to_async
def create_episode():
    return EpisodeFactory()


@database_sync_to_async
def db_cleanup(episode):
    episode.podcast.delete()


def make_communicator(episode, session):
    communicator = WebsocketCommunicator(
        PlayerConsumer.as_asgi(), f"/ws/player/{episode.id}/",
    )
    communicator.scope["session"] = session
    communicator.scope["url_route"] = {"kwargs": {"episode_id": episode.id}}
    return communicator


def make_event(msg_type, episode, request_id, **data):
    return {**data, "episode": episode.id, "request_id": request_id, "type": msg_type}


class TestPlayerConsumer:
    @pytest.mark.asyncio
    async def test_start_player(self, mock_session):

        session = mock_session()
        episode = await create_episode()

        communicator = make_communicator(episode, session)

        await communicator.connect()
        await communicator.send_input(
            make_event("player.start", episode, session.session_key)
        )
        output = await communicator.receive_output()
        assert f"episode-play-buttons-{episode.id}" in output["text"]
        await communicator.disconnect()

        await db_cleanup(episode)

    @pytest.mark.asyncio
    async def test_stop_player(self, mock_session):

        session = mock_session()
        episode = await create_episode()

        communicator = make_communicator(episode, session)

        await communicator.connect()
        await communicator.send_input(
            make_event("player.stop", episode, session.session_key)
        )
        output = await communicator.receive_output()
        assert f"episode-play-buttons-{episode.id}" in output["text"]
        await communicator.disconnect()

        await db_cleanup(episode)
