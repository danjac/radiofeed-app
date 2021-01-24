# Third Party Libraries
import pytest

# Local
from ..middleware import PlayerMiddleware

pytestmark = pytest.mark.django_db


class TestPlayerMiddleware:
    def test_player_in_request(self, rf, get_response):
        req = rf.get("/")
        req.session = {}
        PlayerMiddleware(get_response)(req)
        assert hasattr(req, "player")
