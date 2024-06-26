from django.http import HttpRequest, HttpResponse

from radiofeed.middleware import BaseMiddleware


class AudioPlayerMiddleware(BaseMiddleware):
    """Adds `AudioPlayerDetail` instance to request as `request.audio_player`."""

    def handle_request(self, request: HttpRequest) -> HttpResponse:
        """Middleware implementation."""
        request.audio_player = AudioPlayerDetails(request)
        return self.get_response(request)


class AudioPlayerDetails:
    """Tracks current player episode in session."""

    session_key: str = "audio_player"

    def __init__(self, request: HttpRequest) -> None:
        self.request = request

    def get(self) -> int | None:
        """Returns primary key of episode in player, if any in session."""
        return self.request.session.get(self.session_key)

    def has(self, episode_id: int) -> bool:
        """Checks if episode matching ID is in player."""
        return self.get() == episode_id

    def set(self, episode_id: int) -> None:
        """Adds episode PK to player in session."""
        self.request.session[self.session_key] = episode_id

    def pop(self) -> int | None:
        """Returns primary key of episode in player, if any in session, and removes
        the episode ID from the session."""
        return self.request.session.pop(self.session_key, None)
