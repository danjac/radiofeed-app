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

    async def player_start(self, event):
        await self.send_episode_play_buttons(event, is_playing=True)

    async def player_stop(self, event):
        await self.send_episode_play_buttons(event, is_playing=False)

    async def player_timeupdate(self, event):
        if self.event_matches_request_id(event) and (
            episode := await self.get_episode(event)
        ):
            await self.send_turbo_stream(
                f"episode-current-time-{episode.id}",
                "episodes/_current_time.html",
                {"episode": episode, **event["info"]},
            )

    @database_sync_to_async
    def get_episode(self, event):
        try:
            return Episode.objects.get(pk=event["episode"])
        except Episode.DoesNotExist:
            return None

    async def send_episode_play_buttons(self, event, is_playing):
        if self.event_matches_request_id(event) and (
            episode := await self.get_episode(event)
        ):
            await self.send_turbo_stream(
                f"episode-play-buttons-{episode.id}",
                "episodes/_play_buttons_toggle.html",
                {"episode": episode, "is_playing": is_playing},
            )

    def event_matches_request_id(self, event):
        return self.request_id == event["request_id"]

    async def send_turbo_stream(self, target, template_name, context=None):
        await self.send(
            TurboStream(target).replace.template(template_name, context or {}).render()
        )
