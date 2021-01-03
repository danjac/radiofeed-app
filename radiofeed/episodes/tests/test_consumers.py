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
    communicator = WebsocketCommunicator(PlayerConsumer.as_asgi(), "/ws/player/",)
    communicator.scope["session"] = session
    return communicator


def make_event(msg_type, episode, request_id, **data):
    return {**data, "episode": episode.id, "request_id": request_id, "type": msg_type}


class TestPlayerConsumer:
    @pytest.mark.asyncio
    async def test_player_start(self, mock_session):

        session = mock_session()
        episode = await create_episode()

        communicator = make_communicator(episode, session)

        await communicator.connect()
        await communicator.send_input(
            make_event("player.start", episode, session.session_key)
        )
        output = await communicator.receive_output()
        assert f'target="episode-play-buttons-{episode.id}"' in output["text"]
        await communicator.disconnect()

        await db_cleanup(episode)

    @pytest.mark.asyncio
    async def test_player_stop(self, mock_session):

        session = mock_session()
        episode = await create_episode()

        communicator = make_communicator(episode, session)

        await communicator.connect()
        await communicator.send_input(
            make_event("player.stop", episode, session.session_key)
        )
        output = await communicator.receive_output()
        assert f'target="episode-play-buttons-{episode.id}"' in output["text"]
        await communicator.disconnect()

        await db_cleanup(episode)

    @pytest.mark.asyncio
    async def test_player_timeupdate(self, mock_session):

        session = mock_session()
        episode = await create_episode()

        communicator = make_communicator(episode, session)

        info = {
            "current_time": 1234,
            "completed": False,
            "duration": 10000,
        }

        await communicator.connect()
        await communicator.send_input(
            make_event("player.timeupdate", episode, session.session_key, info=info)
        )
        output = await communicator.receive_output()
        assert f'target="episode-current-time-{episode.id}"' in output["text"]
        await communicator.disconnect()

        await db_cleanup(episode)
