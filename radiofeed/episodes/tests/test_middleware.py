# Third Party Libraries
import pytest

# Local
from ..middleware import PlayerSessionMiddleware

pytestmark = pytest.mark.django_db


class TestPlayerSessionMiddleware:
    def test_player_in_request(self, rf, get_response):
        req = rf.get("/")
        req.session = {}
        PlayerSessionMiddleware(get_response)(req)
        assert hasattr(req, "player")
