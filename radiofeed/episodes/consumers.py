# Third Party Libraries
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from turbo_response import TurboStream

# RadioFeed
from radiofeed.episodes.models import Episode


class PlayerConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.request_id = self.scope["session"].session_key
        await self.channel_layer.group_add("player", self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard("player", self.channel_name)

    @database_sync_to_async
    def get_episode(self, episode_id):
        try:
            return Episode.objects.get(pk=episode_id)
        except Episode.DoesNotExist:
            return None

    def event_matches_request_id(self, event):
        return self.request_id == event["request_id"]

    async def send_episode_play_buttons(self, episode, is_playing):
        await self.send(
            TurboStream(f"episode-play-buttons-{episode.id}")
            .replace.template(
                "episodes/_play_buttons_toggle.html",
                {"episode": episode, "is_episode_playing": is_playing},
            )
            .render()
        )

    async def player_timeupdate(self, event):
        if self.event_matches_request_id(event):
            episode = await self.get_episode(event["episode"])
            await self.send(
                TurboStream(f"episode-current-time-{episode.id}")
                .replace.template(
                    "episodes/_current_time.html",
                    {**event["info"], "episode": episode},
                )
                .render()
            )

    async def player_start(self, event):
        if self.event_matches_request_id(event):
            episode = await self.get_episode(event["episode"])
            await self.send_episode_play_buttons(episode, is_playing=True)

    async def player_stop(self, event):
        if self.event_matches_request_id(event):
            episode = await self.get_episode(event["episode"])
            await self.send_episode_play_buttons(episode, is_playing=False)
