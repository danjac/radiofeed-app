from django.utils.functional import SimpleLazyObject

from radiofeed.common.middleware import BaseMiddleware


class Player:
    """Tracks current player episode in session

    Args:
        request (HttpRequest)
    """

    session_key = "player_episode"

    def __init__(self, request):
        self.request = request

    def get(self):
        """Returns primary key of episode in player, if any in session.

        Returns:
            int | None: episode PK
        """
        return self.request.session.get(self.session_key)

    def set(self, episode_id):
        """Adds episode PK to player in session.

        Args:
            episode_id (int): Episode Pk
        """
        self.request.session[self.session_key] = episode_id

    def has(self, episode_id):
        """Checks if episode matching ID is in player.

        Args:
            episode_id (int): Episode Pk

        Returns:
            bool
        """
        return self.get() == episode_id

    def pop(self):
        """Returns primary key of episode in player, if any in session,
        and removes the episode ID from the session.

        Returns:
            int | None: episode PK
        """
        return self.request.session.pop(self.session_key, None)


class PlayerMiddleware(BaseMiddleware):
    """Adds Player instance to request as `request.player`."""

    def __call__(self, request):
        request.player = SimpleLazyObject(lambda: Player(request))
        return self.get_response(request)
