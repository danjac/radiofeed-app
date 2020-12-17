# Third Party Libraries
# Django
from django.conf import settings
from django.urls import reverse

import pytest

# Local
from .. import views

pytestmark = pytest.mark.django_db


class TestDeleteAccount:
    def test_get(self, rf, user, user_model):
        # make sure we don't accidentally delete account on get request
        req = rf.get(reverse("delete_account"))
        req.user = user
        resp = views.delete_account(req)
        assert resp.status_code == 200
        assert user_model.objects.exists()

    def test_post_unconfirmed(self, rf, user, user_model):
        req = rf.post(reverse("delete_account"))
        req.user = user
        resp = views.delete_account(req)
        assert resp.status_code == 200
        assert user_model.objects.exists()

    def test_post_confirmed(self, rf, user, user_model, mocker):
        req = rf.post(reverse("delete_account"), {"confirm-delete": True})
        req.user = user
        req.session = mocker.Mock()
        req._messages = mocker.Mock()
        resp = views.delete_account(req)
        assert resp.url == settings.HOME_URL
        assert not user_model.objects.exists()
