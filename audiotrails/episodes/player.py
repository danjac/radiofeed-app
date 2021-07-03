from __future__ import annotations

from typing import ClassVar

from django.http import HttpRequest
from django.utils import timezone

from audiotrails.episodes.models import AudioLog, Episode, QueueItem


class Player:
    """Tracks current playing episode in user session"""

    session_key: ClassVar[str] = "player"

    def __init__(self, request: HttpRequest):
        self.request = request

    def start_episode(self, episode: Episode) -> AudioLog:
        """Creates/updates audio log and adds episode to session."""

        session_data = {
            "episode": episode.id,
        }

        QueueItem.objects.filter(
            user=self.request.user,
            episode=episode,
        ).delete()

        self.request.session[self.session_key] = session_data

        log, _ = AudioLog.objects.update_or_create(
            episode=episode,
            user=self.request.user,
            defaults={
                "updated": timezone.now(),
                "completed": None,
            },
        )

        self.current_log = log

        return log

    def stop_episode(self, mark_completed: bool = False) -> AudioLog | None:
        """Removes episode from session and updates log.
        Returns episode.
        """
        if (log := self.get_audio_log()) is None:
            return None

        del self.request.session[self.session_key]

        self.current_log = None

        now = timezone.now()

        log.updated = now

        if mark_completed:
            log.completed = now
            log.current_time = 0

        log.save()

        return log

    def update_current_time(self, current_time: float) -> None:
        if self.request.user.is_authenticated and (
            episode_id := self.get_current_episode_id()
        ):
            AudioLog.objects.filter(
                episode=episode_id,
                user=self.request.user,
            ).update(current_time=round(current_time))

    def is_playing(self, episode: Episode) -> bool:
        return self.get_current_episode_id() == episode.id

    def get_current_episode_id(self) -> int | None:
        return self.get_session_data().get("episode", None)

    def get_session_data(self) -> dict:
        return self.request.session.get(self.session_key, {})

    def get_audio_log(self) -> AudioLog | None:
        if hasattr(self, "current_log"):
            return self.current_log

        if self.request.user.is_anonymous or (
            (episode_id := self.get_current_episode_id()) is None
        ):
            self.current_log = None

        else:
            self.current_log = (
                AudioLog.objects.filter(user=self.request.user, episode=episode_id)
                .select_related("episode", "episode__podcast")
                .first()
            )
        return self.current_log
